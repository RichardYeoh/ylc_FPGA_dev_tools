from __future__ import annotations
import os
import threading
import queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import re
from collections import Counter


TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".tsv",
    ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
    ".java", ".py", ".js", ".ts", ".go", ".rs",
    ".v", ".sv", ".vh", ".vhd", ".vhdl",
    ".tcl", ".sh", ".bat", ".ps1",
    ".json", ".yaml", ".yml", ".ini", ".cfg", ".toml",
    ".xml", ".html", ".htm", ".css", ".scss", ".less",
    ".sql", ".lua", ".mk", ".cmake", ".make",
}

ENCODING_CANDIDATES = [
    "gb18030",
    "gbk",
    "gb2312",
    "big5",
]

AUTHOR_VALUE = "ylcheng"
LINE_COMMENT_RE = re.compile(r"^(?P<indent>\s*//\s*)(?P<body>.*?)(?P<newline>\r?\n?)$")
BLOCK_STYLE_RE = re.compile(
    r"^(?P<prefix>\s*\*\s*)(?P<label>author(?:'s email)?|email)\b(?P<pad>\s*:\s*)(?P<value>.*?)(?P<suffix>\s*)$",
    re.IGNORECASE,
)
LINE_STYLE_RE = re.compile(
    r"^(?P<lead>\s*)(?P<label>author/designer|author(?:'s email)?|email)\b(?P<gap>\s*)(?P<pad>:\s*)(?P<value>.*?)(?P<suffix>\s*)$",
    re.IGNORECASE,
)
COPYRIGHT_RE = re.compile(r"copyright|copyright@|copyright\s*\(c\)|copyright\(c\)", re.IGNORECASE)
COPYRIGHT_FOLLOW_RE = re.compile(r"(confidential|proprietary|all rights reserved)", re.IGNORECASE)
RELEASE_HEADER_RE = re.compile(r"^//(?P<indent>\s*)VERSION\s+Date\s+AUTHOR\s+DESCRIPTION\b", re.IGNORECASE)
RELEASE_ROW_RE = re.compile(r"^//(?P<indent>\s*)\S+\s+\d{4}-\d{2}-\d{2}\s+")
AUTHOR_MATCH_TARGETS = ("yanglicheng", "lichengyang")
AUTHOR_MATCH_THRESHOLD = 8


def is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\x00" in data:
        return True
    ctrl = sum(1 for b in data if b < 9 or (13 < b < 32))
    return (ctrl / max(len(data), 1)) > 0.3


def contains_chinese(text: str) -> bool:
    for ch in text:
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF:
            return True
        if 0x3400 <= code <= 0x4DBF:
            return True
    return False


def decode_bytes(data: bytes):
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass
    for enc in ENCODING_CANDIDATES:
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return None, None


def is_text_extension(path: str) -> bool:
    _, ext = os.path.splitext(path)
    if not ext:
        return True
    return ext.lower() in TEXT_EXTENSIONS


def is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("*/")


def split_header(lines: list[str]) -> tuple[list[str], list[str]]:
    header: list[str] = []
    body_start = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            header.append(line)
            continue
        if is_comment_or_blank(line):
            header.append(line)
            continue
        body_start = idx
        break
    else:
        body_start = len(lines)
    return header, lines[body_start:]


def split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def should_replace_author(value: str) -> bool:
    canonical = re.sub(r"[^a-z]", "", value.lower())
    if not canonical:
        return False
    source_counter = Counter(canonical)
    for target in AUTHOR_MATCH_TARGETS:
        overlap = sum((source_counter & Counter(target)).values())
        if overlap > AUTHOR_MATCH_THRESHOLD:
            return True
    return False


def maybe_rewrite_comment_line(line: str) -> tuple[str | None, bool]:
    match = LINE_COMMENT_RE.match(line)
    if not match:
        return line, False

    body = match.group("body")
    newline = match.group("newline")

    line_style = LINE_STYLE_RE.match(body)
    if line_style:
        label = line_style.group("label").lower()
        if "email" in label:
            return None, True
        if not should_replace_author(line_style.group("value")):
            return line, False
        rebuilt = (
            f"{match.group('indent')}{line_style.group('lead')}{line_style.group('label')}"
            f"{line_style.group('gap')}: {AUTHOR_VALUE}{newline}"
        )
        return rebuilt, rebuilt != line

    block_style = BLOCK_STYLE_RE.match(body)
    if block_style:
        label = block_style.group("label").lower()
        if "email" in label:
            return None, True
        if not should_replace_author(block_style.group("value")):
            return line, False
        rebuilt = (
            f"{match.group('indent')}{block_style.group('prefix')}"
            f"{block_style.group('label')}: {AUTHOR_VALUE}{newline}"
        )
        return rebuilt, rebuilt != line

    if COPYRIGHT_RE.search(body):
        return None, True

    return line, False


def transform_header(lines: list[str]) -> tuple[list[str], bool]:
    updated: list[str] = []
    changed = False
    skip_followup = False
    release_columns: tuple[int, int] | None = None

    for line in lines:
        stripped = line.strip()
        if skip_followup:
            if stripped.startswith("//") and COPYRIGHT_FOLLOW_RE.search(stripped):
                changed = True
                continue
            skip_followup = False

        if release_columns is not None:
            if stripped.startswith("//") and RELEASE_ROW_RE.match(line):
                author_start, desc_start = release_columns
                line_body, newline = split_line_ending(line)
                if len(line_body) >= desc_start:
                    author_field = line_body[author_start:desc_start]
                    if should_replace_author(author_field):
                        new_field = f"{AUTHOR_VALUE:<{len(author_field)}}"
                        rebuilt = f"{line_body[:author_start]}{new_field}{line_body[desc_start:]}{newline}"
                    else:
                        rebuilt = line
                    updated.append(rebuilt)
                    changed = changed or rebuilt != line
                    continue
            else:
                release_columns = None

        rewritten, line_changed = maybe_rewrite_comment_line(line)
        if rewritten is None:
            changed = True
            if COPYRIGHT_RE.search(line):
                skip_followup = True
            continue

        updated.append(rewritten)
        changed = changed or line_changed
        header_match = RELEASE_HEADER_RE.match(rewritten)
        if header_match:
            line_body, _ = split_line_ending(rewritten)
            author_start = line_body.index("AUTHOR")
            desc_start = line_body.index("DESCRIPTION")
            release_columns = (author_start, desc_start)

    return updated, changed


def update_headers(text: str) -> tuple[str, bool]:
    lines = text.splitlines(keepends=True)
    header, body = split_header(lines)
    new_header, changed = transform_header(header)
    if not changed:
        return text, False
    return "".join(new_header + body), True


def should_process_for_encoding(path: str, include_no_ext: bool) -> bool:
    if not is_text_extension(path):
        return False
    if include_no_ext:
        return True
    _, ext = os.path.splitext(path)
    return bool(ext)


def process_directory(
    root_dir: str,
    target_encoding: str,
    include_no_ext: bool,
    update_headers_flag: bool,
    on_log: callable | None = None,
    on_progress: callable | None = None,
):
    stats = {
        "total": 0,
        "processed": 0,
        "converted": 0,
        "already_target": 0,
        "no_chinese": 0,
        "binary": 0,
        "decode_fail": 0,
        "encode_fail": 0,
        "header_updated": 0,
        "skipped_ext": 0,
    }

    def log(msg: str):
        if on_log is None:
            print(msg, end="")
        else:
            on_log(msg)

    all_files = []
    for base, _, files in os.walk(root_dir):
        for name in files:
            path = os.path.join(base, name)
            if not update_headers_flag:
                if not should_process_for_encoding(path, include_no_ext):
                    stats["skipped_ext"] += 1
                    continue
            all_files.append(path)

    stats["total"] = len(all_files)
    if on_progress is not None:
        on_progress(0, stats["total"], "开始处理")
    log(f"扫描到候选文件数：{stats['total']}\n")

    for idx, path in enumerate(all_files, start=1):
        stats["processed"] += 1
        if on_progress is not None:
            on_progress(idx, stats["total"], "处理中")
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError as exc:
            log(f"[读取失败] {path} ({exc})\n")
            continue

        if is_probably_binary(data):
            stats["binary"] += 1
            log(f"[跳过-疑似二进制] {path}\n")
            continue

        text, src_enc = decode_bytes(data)
        if text is None:
            stats["decode_fail"] += 1
            log(f"[解码失败] {path}\n")
            continue

        header_changed = False
        if update_headers_flag:
            text, header_changed = update_headers(text)

        has_cn = contains_chinese(text)
        should_convert = False
        if has_cn:
            if target_encoding == "utf-8":
                should_convert = src_enc != "utf-8"
            else:
                should_convert = src_enc != "gb2312"

        can_process_encoding = should_process_for_encoding(path, include_no_ext)
        if not can_process_encoding:
            stats["skipped_ext"] += 1
            if header_changed:
                try:
                    with open(path, "wb") as f:
                        f.write(text.encode(target_encoding))
                    stats["header_updated"] += 1
                    log(f"[头注释更新] {path}\n")
                except (OSError, UnicodeEncodeError) as exc:
                    stats["encode_fail"] += 1
                    log(f"[写入失败] {path} ({exc})\n")
            continue

        if not should_convert and not header_changed:
            if has_cn:
                label = "已是UTF-8" if target_encoding == "utf-8" else "已是GB2312"
                stats["already_target"] += 1
                log(f"[{label}] {path}\n")
            else:
                stats["no_chinese"] += 1
                log(f"[无中文] {path}\n")
            continue

        try:
            with open(path, "wb") as f:
                f.write(text.encode(target_encoding))
        except (OSError, UnicodeEncodeError) as exc:
            stats["encode_fail"] += 1
            log(f"[写入失败] {path} ({exc})\n")
            continue

        if header_changed and should_convert:
            stats["converted"] += 1
            stats["header_updated"] += 1
            log(f"[已转换+头注释更新] {path} (原编码: {src_enc})\n")
        elif header_changed:
            stats["header_updated"] += 1
            log(f"[头注释更新] {path} (原编码: {src_enc})\n")
        else:
            stats["converted"] += 1
            log(f"[已转换] {path} (原编码: {src_enc})\n")

    summary = (
        "\n处理完成\n"
        f"总候选文件: {stats['total']}\n"
        f"已处理文件: {stats['processed']}\n"
        f"已转换: {stats['converted']}\n"
        f"已是目标编码: {stats['already_target']}\n"
        f"头注释更新: {stats['header_updated']}\n"
        f"无中文跳过: {stats['no_chinese']}\n"
        f"疑似二进制跳过: {stats['binary']}\n"
        f"解码失败: {stats['decode_fail']}\n"
        f"写入失败: {stats['encode_fail']}\n"
        f"扩展名跳过: {stats['skipped_ext']}\n"
    )
    log(summary)
    if on_progress is not None:
        on_progress(stats["total"], stats["total"], "完成")
    return stats


class RtlSrcProcessApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("RTL 源文件处理工具")
        self.root.geometry("900x610")
        self.root.minsize(820, 560)

        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.worker_thread = None
        self.running = False

        self._build_ui()
        self._poll_queues()

    def _build_ui(self):
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        title = ttk.Label(
            self.root,
            text="RTL 源文件处理工具",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(pady=(16, 6))

        subtitle = ttk.Label(
            self.root,
            text="编码转换 + 头注释规范化（可选）",
            font=("Segoe UI", 10),
        )
        subtitle.pack(pady=(0, 10))

        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.X)

        self.dir_var = tk.StringVar(value=str(self._default_rtl_dir()))
        dir_label = ttk.Label(frame, text="目标目录：")
        dir_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 6))

        dir_entry = ttk.Entry(frame, textvariable=self.dir_var)
        dir_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 6))

        browse_btn = ttk.Button(frame, text="选择目录", command=self._select_dir)
        browse_btn.grid(row=0, column=2)

        frame.columnconfigure(1, weight=1)

        options = ttk.LabelFrame(self.root, text="编码处理", padding=(12, 8))
        options.pack(fill=tk.X, padx=12, pady=(0, 6))

        self.encoding_var = tk.StringVar(value="utf-8")
        ttk.Radiobutton(options, text="输出 UTF-8", variable=self.encoding_var, value="utf-8").pack(
            side=tk.LEFT, padx=(4, 12)
        )
        ttk.Radiobutton(options, text="输出 GB2312", variable=self.encoding_var, value="gb2312").pack(
            side=tk.LEFT, padx=(4, 12)
        )

        self.include_no_ext = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options,
            text="包含无后缀文件（若为文本）",
            variable=self.include_no_ext,
        ).pack(side=tk.LEFT, padx=(4, 12))

        header_frame = ttk.LabelFrame(self.root, text="头注释处理", padding=(12, 8))
        header_frame.pack(fill=tk.X, padx=12, pady=(0, 8))

        self.update_headers_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            header_frame,
            text="执行 update_rtl_headers 规则（删除版权/邮箱，作者统一为 ylcheng）",
            variable=self.update_headers_var,
        ).pack(anchor=tk.W)

        control = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        control.pack(fill=tk.X)
        self.start_btn = ttk.Button(control, text="开始处理", command=self._start)
        self.start_btn.pack(side=tk.LEFT)

        self.progress = ttk.Progressbar(control, mode="determinate")
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        self.progress_label = ttk.Label(control, text="等待开始")
        self.progress_label.pack(side=tk.LEFT)

        log_frame = ttk.Frame(self.root, padding=(12, 6, 12, 12))
        log_frame.pack(fill=tk.BOTH, expand=True)

        log_label = ttk.Label(log_frame, text="详细日志：")
        log_label.pack(anchor=tk.W)

        self.log_text = ScrolledText(log_frame, height=18, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.configure(state=tk.DISABLED)

    def _default_rtl_dir(self) -> Path:
        return Path(__file__).resolve().parent / "rtl"

    def _select_dir(self):
        path = filedialog.askdirectory(initialdir=self.dir_var.get())
        if path:
            self.dir_var.set(path)

    def _start(self):
        if self.running:
            return
        root_dir = self.dir_var.get().strip()
        if not root_dir:
            messagebox.showwarning("提示", "请先选择目录。")
            return
        if not os.path.isdir(root_dir):
            messagebox.showerror("错误", "选择的目录不存在。")
            return

        encoding_label = "UTF-8" if self.encoding_var.get() == "utf-8" else "GB2312"
        header_label = "是" if self.update_headers_var.get() else "否"
        confirm = messagebox.askokcancel(
            "确认处理",
            "将递归扫描目录并直接修改文件内容。\n"
            f"目标编码：{encoding_label}\n"
            f"执行头注释规则：{header_label}\n\n"
            "此操作不可自动撤销，是否继续？",
        )
        if not confirm:
            return

        self._reset_ui()
        self.running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(root_dir, self.encoding_var.get(), self.include_no_ext.get(), self.update_headers_var.get()),
            daemon=True,
        )
        self.worker_thread.start()

    def _reset_ui(self):
        self.progress["value"] = 0
        self.progress_label.configure(text="准备中...")
        self._append_log("开始扫描并处理...\n")

    def _append_log(self, text: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        print(text, end="")

    def _poll_queues(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._append_log(msg)
        except queue.Empty:
            pass

        try:
            while True:
                progress = self.progress_queue.get_nowait()
                self._update_progress(progress)
        except queue.Empty:
            pass

        self.root.after(120, self._poll_queues)

    def _update_progress(self, progress):
        value, total, status = progress
        if total > 0:
            self.progress["maximum"] = total
            self.progress["value"] = value
            self.progress_label.configure(text=f"{value}/{total} {status}")
        else:
            self.progress_label.configure(text=status)

    def _worker(self, root_dir: str, target_encoding: str, include_no_ext: bool, update_headers_flag: bool):
        process_directory(
            root_dir,
            target_encoding,
            include_no_ext,
            update_headers_flag,
            on_log=lambda msg: self.log_queue.put(msg),
            on_progress=lambda v, t, s: self.progress_queue.put((v, t, s)),
        )
        self.root.after(0, self._finish)

    def _finish(self):
        self.running = False
        self.start_btn.configure(state=tk.NORMAL)
        messagebox.showinfo("完成", "处理完成，详情请查看日志。")


def main():
    root = tk.Tk()
    app = RtlSrcProcessApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
