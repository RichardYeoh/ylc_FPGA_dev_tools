from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
import queue
import re
import shutil
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


RTL_EXTENSIONS = {".v", ".sv", ".vh", ".svh", ".vhd", ".vhdl"}
VERILOG_EXTENSIONS = {".v", ".sv", ".vh", ".svh"}
VHDL_EXTENSIONS = {".vhd", ".vhdl"}
UTF8_BOM = b"\xef\xbb\xbf"
UTF16_LE_BOM = b"\xff\xfe"
UTF16_BE_BOM = b"\xfe\xff"
UTF32_LE_BOM = b"\xff\xfe\x00\x00"
UTF32_BE_BOM = b"\x00\x00\xfe\xff"
BOM_ENCODINGS = (
    (UTF8_BOM, "utf-8-sig"),
    (UTF32_LE_BOM, "utf-32"),
    (UTF32_BE_BOM, "utf-32"),
    (UTF16_LE_BOM, "utf-16"),
    (UTF16_BE_BOM, "utf-16"),
)
TEXT_ENCODING_CANDIDATES = ("utf-8", "gb18030", "gbk", "gb2312")
FONT_NAME = "Microsoft YaHei UI"
LOG_FONT = "Consolas"
THEME = {
    "bg": "#eef3f8",
    "surface": "#ffffff",
    "accent": "#0f766e",
    "accent_dark": "#115e59",
    "text": "#122033",
    "muted": "#5b6778",
    "border": "#d6deea",
    "progress": "#dce5ef",
    "log_bg": "#f8fbfe",
}


@dataclass
class CleanOptions:
    root: Path
    apply_changes: bool = False
    create_backup: bool = True
    backup_root: Path | None = None
    remove_all_dont_touch: bool = False
    align_local: bool = True
    extensions: set[str] = field(default_factory=lambda: set(RTL_EXTENSIONS))


@dataclass
class TransformStats:
    mark_debug_removed: int = 0
    dont_touch_removed: int = 0
    dont_touch_preserved: int = 0
    keep_removed: int = 0
    keep_preserved: int = 0

    @property
    def changed(self) -> bool:
        return self.mark_debug_removed > 0 or self.dont_touch_removed > 0 or self.keep_removed > 0


@dataclass
class FileReport:
    path: Path
    changed: bool
    stats: TransformStats
    backup_path: Path | None = None
    error: str | None = None
    skipped_reason: str | None = None


@dataclass
class RunReport:
    root: Path
    apply_changes: bool
    total_files: int = 0
    scanned_files: int = 0
    changed_files: list[Path] = field(default_factory=list)
    failed_files: list[tuple[Path, str]] = field(default_factory=list)
    skipped_files: list[tuple[Path, str]] = field(default_factory=list)
    backup_files: list[Path] = field(default_factory=list)
    mark_debug_removed: int = 0
    dont_touch_removed: int = 0
    dont_touch_preserved: int = 0
    keep_removed: int = 0
    keep_preserved: int = 0
    duration_sec: float = 0.0
    cancelled: bool = False

    def snapshot(self) -> dict[str, int]:
        return {
            "total": self.total_files,
            "scanned": self.scanned_files,
            "changed": len(self.changed_files),
            "mark_debug": self.mark_debug_removed,
            "dont_touch": self.dont_touch_removed,
            "keep": self.keep_removed,
            "failures": len(self.failed_files),
            "backups": len(self.backup_files),
        }


def is_identifier_char(value: str) -> bool:
    return value.isalnum() or value in "_$"


def is_verilog_file(path: Path) -> bool:
    return path.suffix.lower() in VERILOG_EXTENSIONS


def is_vhdl_file(path: Path) -> bool:
    return path.suffix.lower() in VHDL_EXTENSIONS


def is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    if any(data.startswith(signature) for signature, _encoding in BOM_ENCODINGS):
        return False
    if b"\x00" in data:
        return True
    # Control-byte ratio filter / 控制字节比例过滤
    ctrl = sum(1 for value in data if value < 9 or (13 < value < 32))
    return ctrl / max(len(data), 1) > 0.30


def decode_source(data: bytes) -> tuple[str, str]:
    for signature, encoding in BOM_ENCODINGS:
        if data.startswith(signature):
            return data.decode(encoding), encoding
    last_error: Exception | None = None
    for encoding in TEXT_ENCODING_CANDIDATES:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeDecodeError("source", data, 0, 1, f"cannot decode source file: {last_error}")


def encode_source(text: str, encoding: str) -> bytes:
    return text.encode(encoding)


def iter_source_files(root: Path, extensions: set[str]) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in extensions)


def split_attribute_items(content: str) -> list[str]:
    items: list[str] = []
    start = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(content):
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            continue
        if char == ",":
            items.append(content[start:index])
            start = index + 1
    items.append(content[start:])
    return items


def get_attribute_name(item: str) -> str | None:
    match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_$]*)\b", item)
    if not match:
        return None
    return match.group(1).lower()


def process_attribute_content(
    content: str,
    remove_dont_touch: bool,
    remove_keep: bool,
    stats: TransformStats,
) -> str | None:
    kept_items: list[str] = []
    for item in split_attribute_items(content):
        name = get_attribute_name(item)
        if name == "mark_debug":
            stats.mark_debug_removed += 1
            continue
        if name == "dont_touch":
            if remove_dont_touch:
                stats.dont_touch_removed += 1
                continue
            stats.dont_touch_preserved += 1
        if name == "keep":
            if remove_keep:
                stats.keep_removed += 1
                continue
            stats.keep_preserved += 1
        if item.strip():
            kept_items.append(item.strip())
    if not kept_items:
        return None
    return "(* " + ", ".join(kept_items) + " *)"


def find_attribute_end(text: str, start: int) -> int:
    end = text.find("*)", start + 2)
    return -1 if end < 0 else end + 2


def collect_attribute_group(text: str, start: int) -> tuple[list[tuple[int, int, str]], int]:
    blocks: list[tuple[int, int, str]] = []
    cursor = start
    while cursor < len(text) and text.startswith("(*", cursor):
        end = find_attribute_end(text, cursor)
        if end < 0:
            break
        blocks.append((cursor, end, text[cursor + 2 : end - 2]))
        cursor = end
        gap_start = cursor
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if not text.startswith("(*", cursor):
            return blocks, gap_start
    if blocks:
        return blocks, blocks[-1][1]
    return blocks, start


def attribute_group_has_name(blocks: list[tuple[int, int, str]], target_name: str) -> bool:
    target = target_name.lower()
    for _, _, content in blocks:
        for item in split_attribute_items(content):
            if get_attribute_name(item) == target:
                return True
    return False


def need_space_between(left: str, right: str) -> bool:
    return bool(left and right and is_identifier_char(left) and is_identifier_char(right))


def strip_trailing_horizontal_space(text: str) -> str:
    return re.sub(r"[ \t]+(?=\r?\n)", "", text)


def normalize_changed_lines(text: str, touched_lines: set[int]) -> str:
    lines = text.splitlines(keepends=True)
    normalized: list[str] = []
    for line_index, line in enumerate(lines):
        if line_index not in touched_lines:
            normalized.append(line)
            continue
        body = line[:-2] if line.endswith("\r\n") else line[:-1] if line.endswith("\n") else line
        ending = line[len(body) :]
        body = re.sub(r"([,(])\s{2,}(?=(input|output|inout|wire|reg|logic)\b)", r"\1", body)
        body = re.sub(r"^\s+(?=;?$)", "", body)
        normalized.append(body.rstrip(" \t") + ending)
    return "".join(normalized)


def transform_verilog(text: str, options: CleanOptions) -> tuple[str, TransformStats]:
    stats = TransformStats()
    output: list[str] = []
    touched_lines: set[int] = set()
    index = 0
    state = "code"
    quote = ""
    escaped = False

    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""

        if state == "line_comment":
            output.append(char)
            index += 1
            if char == "\n":
                state = "code"
            continue
        if state == "block_comment":
            output.append(char)
            if char == "*" and nxt == "/":
                output.append(nxt)
                index += 2
                state = "code"
            else:
                index += 1
            continue
        if state == "string":
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                state = "code"
            index += 1
            continue

        if char == "/" and nxt == "/":
            output.append(char)
            output.append(nxt)
            index += 2
            state = "line_comment"
            continue
        if char == "/" and nxt == "*":
            output.append(char)
            output.append(nxt)
            index += 2
            state = "block_comment"
            continue
        if char == '"':
            output.append(char)
            quote = char
            escaped = False
            index += 1
            state = "string"
            continue
        if char == "(" and nxt == "*":
            blocks, group_end = collect_attribute_group(text, index)
            if not blocks:
                output.append(char)
                index += 1
                continue
            has_mark_debug = attribute_group_has_name(blocks, "mark_debug")
            has_dont_touch = attribute_group_has_name(blocks, "dont_touch")
            has_keep = attribute_group_has_name(blocks, "keep")
            remove_dont_touch = options.remove_all_dont_touch or has_mark_debug
            remove_keep = has_mark_debug
            if has_mark_debug or (options.remove_all_dont_touch and has_dont_touch):
                start_line = text.count("\n", 0, index)
                end_line = text.count("\n", 0, group_end)
                touched_lines.update(range(start_line, end_line + 1))
                rebuilt_blocks: list[str] = []
                for _, _, content in blocks:
                    rebuilt = process_attribute_content(content, remove_dont_touch, remove_keep, stats)
                    if rebuilt is not None:
                        rebuilt_blocks.append(rebuilt)
                replacement = " ".join(rebuilt_blocks)
                left = output[-1] if output else ""
                right = text[group_end] if group_end < len(text) else ""
                if replacement:
                    if right and not right.isspace() and right not in ";,)]}":
                        replacement += " "
                elif need_space_between(left, right):
                    replacement = " "
                output.append(replacement)
                index = group_end
                continue
            if has_dont_touch:
                for _, _, content in blocks:
                    for item in split_attribute_items(content):
                        if get_attribute_name(item) == "dont_touch":
                            stats.dont_touch_preserved += 1
            if has_keep:
                for _, _, content in blocks:
                    for item in split_attribute_items(content):
                        if get_attribute_name(item) == "keep":
                            stats.keep_preserved += 1
            output.append(text[index:group_end])
            index = group_end
            continue

        output.append(char)
        index += 1

    new_text = "".join(output)
    if not stats.changed:
        return text, stats
    if options.align_local:
        new_text = normalize_changed_lines(new_text, touched_lines)
    return new_text, stats


VHDL_ATTR_DECL_RE = re.compile(r"^\s*attribute\s+(mark_debug|dont_touch|keep)\s*:\s*\w+\s*;\s*$", re.IGNORECASE)
VHDL_ATTR_SPEC_RE = re.compile(
    r"^\s*attribute\s+(mark_debug|dont_touch|keep)\s+of\s+(.+?)\s*:\s*([A-Za-z_][A-Za-z0-9_]*)\s+is\s+(.+?)\s*;\s*$",
    re.IGNORECASE,
)


def split_vhdl_comment(line: str) -> tuple[str, str]:
    quote: str | None = None
    index = 0
    while index < len(line) - 1:
        char = line[index]
        if quote:
            if char == quote:
                quote = None
            index += 1
            continue
        if char in ('"', "'"):
            quote = char
            index += 1
            continue
        if char == "-" and line[index + 1] == "-":
            return line[:index], line[index:]
        index += 1
    return line, ""


def vhdl_object_key(object_name: str, object_class: str) -> tuple[str, str]:
    compact = re.sub(r"\s+", " ", object_name.strip()).lower()
    return compact, object_class.strip().lower()


def get_vhdl_attr_spec(line: str) -> tuple[str, tuple[str, str]] | None:
    code, comment = split_vhdl_comment(line.rstrip("\r\n"))
    if comment and not code.strip():
        return None
    match = VHDL_ATTR_SPEC_RE.match(code.strip())
    if not match:
        return None
    attr_name = match.group(1).lower()
    return attr_name, vhdl_object_key(match.group(2), match.group(3))


def transform_vhdl(text: str, options: CleanOptions) -> tuple[str, TransformStats]:
    stats = TransformStats()
    lines = text.splitlines(keepends=True)
    mark_debug_objects: set[tuple[str, str]] = set()
    dont_touch_objects: set[tuple[str, str]] = set()
    keep_objects: set[tuple[str, str]] = set()

    for line in lines:
        spec = get_vhdl_attr_spec(line)
        if spec is None:
            continue
        attr_name, key = spec
        if attr_name == "mark_debug":
            mark_debug_objects.add(key)
        elif attr_name == "dont_touch":
            dont_touch_objects.add(key)
        elif attr_name == "keep":
            keep_objects.add(key)

    remove_dont_touch_objects = dont_touch_objects if options.remove_all_dont_touch else mark_debug_objects & dont_touch_objects
    keep_dont_touch_objects = dont_touch_objects - remove_dont_touch_objects
    remove_keep_objects = mark_debug_objects & keep_objects
    keep_keep_objects = keep_objects - remove_keep_objects
    output: list[str] = []
    for line in lines:
        ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        body = line[: -len(ending)] if ending else line
        code, comment = split_vhdl_comment(body)
        stripped = code.strip()
        decl_match = VHDL_ATTR_DECL_RE.match(stripped)
        if decl_match:
            attr_name = decl_match.group(1).lower()
            if attr_name == "mark_debug":
                stats.mark_debug_removed += 1
                continue
            if attr_name == "dont_touch" and options.remove_all_dont_touch and not keep_dont_touch_objects:
                stats.dont_touch_removed += 1
                continue
            if attr_name == "dont_touch" and remove_dont_touch_objects and not keep_dont_touch_objects:
                stats.dont_touch_removed += 1
                continue
            if attr_name == "keep" and remove_keep_objects and not keep_keep_objects:
                stats.keep_removed += 1
                continue
        spec = get_vhdl_attr_spec(line)
        if spec is not None:
            attr_name, key = spec
            if attr_name == "mark_debug":
                stats.mark_debug_removed += 1
                continue
            if attr_name == "dont_touch":
                if options.remove_all_dont_touch or key in remove_dont_touch_objects:
                    stats.dont_touch_removed += 1
                    continue
                stats.dont_touch_preserved += 1
            if attr_name == "keep":
                if key in remove_keep_objects:
                    stats.keep_removed += 1
                    continue
                stats.keep_preserved += 1
        output.append(code.rstrip(" \t") + comment + ending)

    if not stats.changed:
        return text, stats
    return "".join(output), stats


def transform_text(path: Path, text: str, options: CleanOptions) -> tuple[str, TransformStats]:
    if is_verilog_file(path):
        return transform_verilog(text, options)
    if is_vhdl_file(path):
        return transform_vhdl(text, options)
    return text, TransformStats()


def default_backup_root(root: Path) -> Path:
    return root.resolve().parent / "debug_version"


def next_backup_path(source_path: Path, root: Path, backup_root: Path) -> Path:
    rel_path = source_path.resolve().relative_to(root.resolve())
    target = backup_root / rel_path
    target = target.with_name(target.name + ".bak")
    if not target.exists():
        return target
    index = 1
    while True:
        candidate = target.with_name(target.name + str(index))
        if not candidate.exists():
            return candidate
        index += 1


def backup_file(source_path: Path, root: Path, backup_root: Path) -> Path:
    target = next_backup_path(source_path, root, backup_root)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    return target


def process_one_file(path: Path, options: CleanOptions) -> FileReport:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return FileReport(path=path, changed=False, stats=TransformStats(), error=f"读取失败: {exc}")
    if is_probably_binary(data):
        return FileReport(path=path, changed=False, stats=TransformStats(), skipped_reason="疑似二进制文件")
    try:
        text, encoding = decode_source(data)
    except UnicodeDecodeError as exc:
        return FileReport(path=path, changed=False, stats=TransformStats(), error=f"解码失败: {exc}")

    new_text, stats = transform_text(path, text, options)
    if new_text == text:
        stats.mark_debug_removed = 0
        stats.dont_touch_removed = 0
        stats.keep_removed = 0
        return FileReport(path=path, changed=False, stats=stats)
    if not options.apply_changes:
        return FileReport(path=path, changed=True, stats=stats)

    backup_path = None
    if options.create_backup:
        try:
            backup_path = backup_file(path, options.root, options.backup_root or default_backup_root(options.root))
        except OSError as exc:
            return FileReport(path=path, changed=False, stats=TransformStats(), error=f"备份失败: {exc}")
    try:
        path.write_bytes(encode_source(new_text, encoding))
    except (OSError, UnicodeEncodeError) as exc:
        return FileReport(path=path, changed=False, stats=TransformStats(), error=f"写入失败: {exc}")
    return FileReport(path=path, changed=True, stats=stats, backup_path=backup_path)


def merge_file_report(run_report: RunReport, file_report: FileReport) -> None:
    run_report.scanned_files += 1
    if file_report.error:
        run_report.failed_files.append((file_report.path, file_report.error))
        return
    if file_report.skipped_reason:
        run_report.skipped_files.append((file_report.path, file_report.skipped_reason))
        return
    run_report.mark_debug_removed += file_report.stats.mark_debug_removed
    run_report.dont_touch_removed += file_report.stats.dont_touch_removed
    run_report.dont_touch_preserved += file_report.stats.dont_touch_preserved
    run_report.keep_removed += file_report.stats.keep_removed
    run_report.keep_preserved += file_report.stats.keep_preserved
    if file_report.changed:
        run_report.changed_files.append(file_report.path)
    if file_report.backup_path is not None:
        run_report.backup_files.append(file_report.backup_path)


def run_clean(
    options: CleanOptions,
    on_log: callable | None = None,
    on_progress: callable | None = None,
    stop_event: threading.Event | None = None,
) -> RunReport:
    start_time = time.perf_counter()
    root = options.root.resolve()
    backup_root = options.backup_root or default_backup_root(root)
    options = CleanOptions(
        root=root,
        apply_changes=options.apply_changes,
        create_backup=options.create_backup,
        backup_root=backup_root,
        remove_all_dont_touch=options.remove_all_dont_touch,
        align_local=options.align_local,
        extensions=set(options.extensions),
    )

    def log(message: str) -> None:
        if on_log is None:
            print(message)
        else:
            on_log(message)

    files = iter_source_files(root, options.extensions)
    report = RunReport(root=root, apply_changes=options.apply_changes, total_files=len(files))
    mode = "写回" if options.apply_changes else "预览"
    log(f"[{mode}] 源目录: {root}")
    log(f"[{mode}] 备份目录: {backup_root}")
    log(f"[{mode}] 候选文件: {len(files)}")

    for index, path in enumerate(files, start=1):
        if stop_event is not None and stop_event.is_set():
            report.cancelled = True
            log("[取消] 收到停止请求，已结束后续扫描。")
            break
        file_report = process_one_file(path, options)
        merge_file_report(report, file_report)
        if file_report.error:
            log(f"[失败] {path} ({file_report.error})")
        elif file_report.skipped_reason:
            log(f"[跳过] {path} ({file_report.skipped_reason})")
        elif file_report.changed:
            action = "将修改" if not options.apply_changes else "已修改"
            backup_note = f", 备份: {file_report.backup_path}" if file_report.backup_path else ""
            log(
                f"[{action}] {path} "
                f"(MARK_DEBUG -{file_report.stats.mark_debug_removed}, "
                f"dont_touch -{file_report.stats.dont_touch_removed}, "
                f"KEEP -{file_report.stats.keep_removed}{backup_note})"
            )
        if on_progress is not None:
            on_progress(index, len(files), report.snapshot())

    report.duration_sec = time.perf_counter() - start_time
    log(format_summary(report, backup_root))
    return report


def format_summary(report: RunReport, backup_root: Path) -> str:
    title = "处理已取消" if report.cancelled else "处理完成"
    mode = "写回" if report.apply_changes else "预览"
    return (
        "\n"
        f"{title}\n"
        f"模式: {mode}\n"
        f"源目录: {report.root}\n"
        f"备份目录: {backup_root}\n"
        f"候选文件: {report.total_files}\n"
        f"已扫描: {report.scanned_files}\n"
        f"命中文件: {len(report.changed_files)}\n"
        f"删除 MARK_DEBUG: {report.mark_debug_removed}\n"
        f"删除 dont_touch: {report.dont_touch_removed}\n"
        f"保留独立 dont_touch: {report.dont_touch_preserved}\n"
        f"删除 KEEP: {report.keep_removed}\n"
        f"保留独立 KEEP: {report.keep_preserved}\n"
        f"备份文件: {len(report.backup_files)}\n"
        f"跳过文件: {len(report.skipped_files)}\n"
        f"失败文件: {len(report.failed_files)}\n"
        f"耗时: {report.duration_sec:.2f}s\n"
    )


class RemoveDebugFlagsApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("RTL Debug 标记清理工具")
        self.root.geometry("1050x740")
        self.root.minsize(920, 650)
        self.root.configure(bg=THEME["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.progress_queue: queue.Queue[tuple[int, int, dict[str, int]]] = queue.Queue()
        self.finish_queue: queue.Queue[RunReport | Exception] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.running = False

        self.source_dir_var = tk.StringVar(value=str((Path.cwd() / "rtl").resolve()))
        self.backup_dir_var = tk.StringVar()
        self.apply_var = tk.BooleanVar(value=False)
        self.backup_var = tk.BooleanVar(value=True)
        self.remove_all_dont_touch_var = tk.BooleanVar(value=False)
        self.align_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="等待扫描")
        self.metric_vars = {
            key: tk.StringVar(value="0")
            for key in ("total", "scanned", "changed", "mark_debug", "dont_touch", "keep", "failures", "backups")
        }
        self._setup_styles()
        self._build_ui()
        self._refresh_backup_dir()
        self._poll_queues()

    def _setup_styles(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("App.TFrame", background=THEME["bg"])
        style.configure("Card.TFrame", background=THEME["surface"])
        style.configure("Hero.TFrame", background=THEME["accent"])
        style.configure("HeroSmall.TLabel", background=THEME["accent"], foreground="#d7f3ee", font=(FONT_NAME, 10, "bold"))
        style.configure("HeroTitle.TLabel", background=THEME["accent"], foreground="#ffffff", font=(FONT_NAME, 22, "bold"))
        style.configure("HeroText.TLabel", background=THEME["accent"], foreground="#d7f3ee", font=(FONT_NAME, 10))
        style.configure("CardTitle.TLabel", background=THEME["surface"], foreground=THEME["text"], font=(FONT_NAME, 13, "bold"))
        style.configure("Hint.TLabel", background=THEME["surface"], foreground=THEME["muted"], font=(FONT_NAME, 9))
        style.configure("Body.TLabel", background=THEME["surface"], foreground=THEME["text"], font=(FONT_NAME, 10))
        style.configure("Accent.TButton", background=THEME["accent"], foreground="#ffffff", borderwidth=0, padding=(14, 9), font=(FONT_NAME, 10, "bold"))
        style.map("Accent.TButton", background=[("active", THEME["accent_dark"]), ("disabled", "#8db5b0")])
        style.configure("Soft.TButton", background="#e5edf5", foreground=THEME["text"], borderwidth=0, padding=(12, 8), font=(FONT_NAME, 10))
        style.configure("Modern.TEntry", fieldbackground="#f8fbfe", foreground=THEME["text"], bordercolor=THEME["border"], padding=8)
        style.configure("Modern.TCheckbutton", background=THEME["surface"], foreground=THEME["text"], font=(FONT_NAME, 10))
        style.configure("Modern.Horizontal.TProgressbar", troughcolor=THEME["progress"], background=THEME["accent"], thickness=12)
        style.configure("MetricValue.TLabel", background=THEME["surface"], foreground=THEME["accent_dark"], font=(FONT_NAME, 18, "bold"))
        style.configure("MetricKey.TLabel", background=THEME["surface"], foreground=THEME["muted"], font=(FONT_NAME, 9))

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, style="App.TFrame", padding=18)
        container.pack(fill=tk.BOTH, expand=True)
        hero = ttk.Frame(container, style="Hero.TFrame", padding=(22, 20))
        hero.pack(fill=tk.X)
        ttk.Label(hero, text="RTL DEBUG CLEANER", style="HeroSmall.TLabel").pack(anchor=tk.W)
        ttk.Label(hero, text="RTL Debug 标记清理工具", style="HeroTitle.TLabel").pack(anchor=tk.W, pady=(6, 4))
        ttk.Label(hero, text="递归扫描 Verilog/SystemVerilog/VHDL 源码，清除 MARK_DEBUG 及配套 dont_touch/KEEP。", style="HeroText.TLabel").pack(anchor=tk.W)

        body = ttk.Frame(container, style="App.TFrame")
        body.pack(fill=tk.BOTH, expand=True, pady=(16, 0))
        body.columnconfigure(0, weight=7)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(2, weight=1)

        target = self._make_card(body, 0, 0, "处理目标", "选择需要扫描的 RTL 根目录。")
        target.columnconfigure(1, weight=1)
        ttk.Label(target, text="源目录", style="Body.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        source_entry = ttk.Entry(target, textvariable=self.source_dir_var, style="Modern.TEntry")
        source_entry.grid(row=2, column=1, sticky="ew", pady=(10, 0), padx=(0, 10))
        source_entry.bind("<FocusOut>", lambda _event: self._refresh_backup_dir())
        ttk.Button(target, text="选择目录", style="Soft.TButton", command=self._browse_source).grid(row=2, column=2, sticky="e", pady=(10, 0))
        ttk.Label(target, text="备份目录", style="Body.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        ttk.Label(target, textvariable=self.backup_dir_var, style="Body.TLabel").grid(row=3, column=1, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Label(target, text="默认备份到源目录同级 debug_version，并保持源目录内部相对结构。", style="Hint.TLabel").grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))

        control = self._make_card(body, 1, 0, "执行控制", "先预览确认，再切换写回模式执行。")
        control.columnconfigure(0, weight=1)
        self.start_btn = ttk.Button(control, text="开始", style="Accent.TButton", command=self._start)
        self.start_btn.grid(row=2, column=0, sticky="w", pady=(10, 12))
        self.stop_btn = ttk.Button(control, text="停止任务", style="Soft.TButton", command=self._stop)
        self.stop_btn.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(10, 12))
        self.stop_btn.configure(state=tk.DISABLED)
        self.progress = ttk.Progressbar(control, mode="determinate", style="Modern.Horizontal.TProgressbar")
        self.progress.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Label(control, textvariable=self.status_var, style="Hint.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        log_card = self._make_card(body, 2, 0, "详细日志", "逐文件输出命中、备份、失败和汇总结果。", fill=True)
        log_card.rowconfigure(3, weight=1)
        log_card.columnconfigure(0, weight=1)
        header = ttk.Frame(log_card, style="Card.TFrame")
        header.grid(row=2, column=0, sticky="ew", pady=(8, 10))
        ttk.Label(header, text="实时日志", style="Body.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="清空日志", style="Soft.TButton", command=self._clear_log).pack(side=tk.RIGHT)
        self.log_text = ScrolledText(log_card, height=18, wrap=tk.WORD, font=(LOG_FONT, 10), background=THEME["log_bg"], foreground=THEME["text"], insertbackground=THEME["text"], relief=tk.FLAT, highlightthickness=1, highlightbackground=THEME["border"], padx=12, pady=10)
        self.log_text.grid(row=3, column=0, sticky="nsew")
        self.log_text.configure(state=tk.DISABLED)

        options = self._make_card(body, 0, 1, "处理选项", "默认保守清理，避免引入无关 diff。")
        ttk.Checkbutton(options, text="写回修改", variable=self.apply_var, style="Modern.TCheckbutton").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Checkbutton(options, text="写回前备份到 debug_version", variable=self.backup_var, style="Modern.TCheckbutton").grid(row=3, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(options, text="移除全部 dont_touch", variable=self.remove_all_dont_touch_var, style="Modern.TCheckbutton").grid(row=4, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(options, text="局部整理空白", variable=self.align_var, style="Modern.TCheckbutton").grid(row=5, column=0, sticky="w", pady=(8, 0))
        ttk.Label(options, text="未勾选写回时只做预览，不修改 RTL。默认仅删除与 MARK_DEBUG 伴随的 dont_touch 和 KEEP。", style="Hint.TLabel", wraplength=330).grid(row=6, column=0, sticky="w", pady=(12, 0))

        summary = self._make_card(body, 1, 1, "结果概览", "执行过程中持续刷新关键统计。")
        metrics = [("候选", "total"), ("已扫", "scanned"), ("命中", "changed"), ("MARK_DEBUG", "mark_debug"), ("dont_touch", "dont_touch"), ("KEEP", "keep"), ("失败", "failures"), ("备份", "backups")]
        for index, (label, key) in enumerate(metrics):
            block = ttk.Frame(summary, style="Card.TFrame")
            block.grid(row=2 + index // 2, column=index % 2, sticky="w", padx=(0, 18), pady=(10 if index < 2 else 12, 0))
            ttk.Label(block, text=label, style="MetricKey.TLabel").pack(anchor=tk.W)
            ttk.Label(block, textvariable=self.metric_vars[key], style="MetricValue.TLabel").pack(anchor=tk.W)

        hint = self._make_card(body, 2, 1, "清理边界", "只移除 debug 属性文本，不修改 RTL 行为。", fill=True)
        text = (
            "处理范围:\n"
            "1. Verilog/SystemVerilog: (* MARK_DEBUG ... *)\n"
            "2. VHDL: attribute mark_debug ...\n"
            "3. 默认移除配套 dont_touch/KEEP\n"
            "4. 保留独立 dont_touch/KEEP\n"
            "5. 注释和字符串中的关键字不处理\n"
            "6. 写回前按相对路径备份到 debug_version"
        )
        ttk.Label(hint, text=text, style="Body.TLabel", justify=tk.LEFT).grid(row=2, column=0, sticky="nw", pady=(8, 0))

    def _make_card(self, parent: ttk.Frame, row: int, column: int, title: str, subtitle: str, fill: bool = False) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        sticky = "nsew" if fill else "ew"
        card.grid(row=row, column=column, sticky=sticky, padx=(0, 14 if column == 0 else 0), pady=(0, 14))
        ttk.Label(card, text=title, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, text=subtitle, style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        return card

    def _browse_source(self) -> None:
        path = filedialog.askdirectory(initialdir=self.source_dir_var.get() or str(Path.cwd()))
        if path:
            self.source_dir_var.set(path)
            self._refresh_backup_dir()

    def _refresh_backup_dir(self) -> None:
        source = Path(self.source_dir_var.get().strip() or ".")
        self.backup_dir_var.set(str(default_backup_root(source)))

    def _clear_log(self) -> None:
        if self.running:
            return
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        print(message)

    def _update_metrics(self, snapshot: dict[str, int]) -> None:
        for key, var in self.metric_vars.items():
            var.set(str(snapshot.get(key, 0)))

    def _start(self) -> None:
        if self.running:
            return
        source = Path(self.source_dir_var.get().strip())
        backup = default_backup_root(source)
        self.backup_dir_var.set(str(backup))
        if not source.exists() or not source.is_dir():
            messagebox.showerror("目录无效", "请选择有效的源目录。")
            return
        backup_line = f"\n备份目录: {backup}" if self.apply_var.get() and self.backup_var.get() else ""
        if self.apply_var.get():
            confirm = f"源目录: {source}\n模式: 写回修改{backup_line}\n\n写回将修改命中的 RTL 文件。是否继续？"
            if not messagebox.askokcancel("确认写回", confirm):
                return
        self._clear_log()
        self._update_metrics({})
        self.progress.configure(maximum=1, value=0)
        self.status_var.set("准备中...")
        self.stop_event.clear()
        self.running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        options = CleanOptions(
            root=source,
            apply_changes=self.apply_var.get(),
            create_backup=self.backup_var.get(),
            backup_root=backup,
            remove_all_dont_touch=self.remove_all_dont_touch_var.get(),
            align_local=self.align_var.get(),
        )
        self.worker_thread = threading.Thread(target=self._worker, args=(options,), daemon=True)
        self.worker_thread.start()

    def _worker(self, options: CleanOptions) -> None:
        try:
            report = run_clean(
                options,
                on_log=self.log_queue.put,
                on_progress=lambda current, total, snapshot: self.progress_queue.put((current, total, snapshot)),
                stop_event=self.stop_event,
            )
            self.finish_queue.put(report)
        except Exception as exc:  # Defensive GUI boundary / GUI 防御性边界
            self.finish_queue.put(exc)

    def _stop(self) -> None:
        if not self.running:
            return
        self.stop_event.set()
        self.status_var.set("停止请求已发送，等待当前文件处理结束...")
        self.stop_btn.configure(state=tk.DISABLED)

    def _poll_queues(self) -> None:
        try:
            while True:
                self._append_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                current, total, snapshot = self.progress_queue.get_nowait()
                self.progress.configure(maximum=max(total, 1), value=min(current, max(total, 1)))
                self.status_var.set(f"正在处理 {current}/{total}")
                self._update_metrics(snapshot)
        except queue.Empty:
            pass
        try:
            while True:
                result = self.finish_queue.get_nowait()
                self._finish(result)
        except queue.Empty:
            pass
        self.root.after(120, self._poll_queues)

    def _finish(self, result: RunReport | Exception) -> None:
        self.running = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        if isinstance(result, Exception):
            self.status_var.set("执行失败")
            messagebox.showerror("执行失败", str(result))
            return
        self.status_var.set("已取消" if result.cancelled else "完成")
        mode = "写回" if result.apply_changes else "预览"
        summary = (
            f"模式: {mode}\n"
            f"候选文件: {result.total_files}\n"
            f"命中文件: {len(result.changed_files)}\n"
            f"删除 MARK_DEBUG: {result.mark_debug_removed}\n"
            f"删除 dont_touch: {result.dont_touch_removed}\n"
            f"删除 KEEP: {result.keep_removed}\n"
            f"备份文件: {len(result.backup_files)}\n"
            f"失败文件: {len(result.failed_files)}"
        )
        messagebox.showinfo("处理报告", summary)

    def _on_close(self) -> None:
        if self.running and not messagebox.askokcancel("确认退出", "当前任务仍在执行中，是否退出？"):
            return
        self.root.destroy()


def launch_gui() -> None:
    root = tk.Tk()
    RemoveDebugFlagsApp(root)
    root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remove Vivado MARK_DEBUG attributes from RTL source files.")
    parser.add_argument("root", nargs="?", default="rtl", help="RTL root directory.")
    parser.add_argument("--gui", action="store_true", help="Launch Tkinter GUI.")
    parser.add_argument("--check", action="store_true", help="Preview only. This is the default.")
    parser.add_argument("--apply", action="store_true", help="Write changes in place.")
    parser.add_argument("--backup", action="store_true", help="Create backup files before writing.")
    parser.add_argument("--no-backup", action="store_true", help="Do not create backup files when applying.")
    parser.add_argument("--remove-all-dont-touch", action="store_true", help="Remove all dont_touch attributes, not only MARK_DEBUG companions.")
    parser.add_argument("--no-align", action="store_true", help="Disable local whitespace cleanup.")
    parser.add_argument("--extensions", default=",".join(sorted(RTL_EXTENSIONS)), help="Comma-separated extension list.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.gui:
        launch_gui()
        return 0
    extensions = {item.strip().lower() for item in args.extensions.split(",") if item.strip()}
    root = Path(args.root)
    apply_changes = bool(args.apply)
    create_backup = not args.no_backup if apply_changes else False
    if args.backup:
        create_backup = True
    options = CleanOptions(
        root=root,
        apply_changes=apply_changes,
        create_backup=create_backup,
        backup_root=None,
        remove_all_dont_touch=args.remove_all_dont_touch,
        align_local=not args.no_align,
        extensions=extensions,
    )
    report = run_clean(options)
    return 2 if report.failed_files else 0


if __name__ == "__main__":
    raise SystemExit(main())
