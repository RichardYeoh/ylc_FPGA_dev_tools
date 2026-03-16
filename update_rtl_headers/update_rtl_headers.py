from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import re
from pathlib import Path
import threading
import time
import queue


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
COPYRIGHT_FOLLOW_RE = re.compile(
    r"(confidential|proprietary|all rights reserved)",
    re.IGNORECASE,
)
RELEASE_HEADER_RE = re.compile(r"^//(?P<indent>\s*)VERSION\s+Date\s+AUTHOR\s+DESCRIPTION\b", re.IGNORECASE)
RELEASE_ROW_RE = re.compile(r"^//(?P<indent>\s*)\S+\s+\d{4}-\d{2}-\d{2}\s+")
AUTHOR_MATCH_TARGETS = ("yanglicheng", "lichengyang")
AUTHOR_MATCH_THRESHOLD = 8

DEFAULT_LABELS = {
    "apply_mode": "APPLY",
    "check_mode": "CHECK",
    "root": "root",
    "scanned": "scanned source files",
    "updated": "updated",
    "would_update": "would update",
    "files": "file(s)",
}

CHINESE_LABELS = {
    "apply_mode": "执行",
    "check_mode": "检查",
    "root": "目录",
    "scanned": "扫描文件数",
    "updated": "已更新",
    "would_update": "可更新",
    "files": "个",
}


@dataclass
class RunReport:
    root: Path
    total_files: int
    changed_files: list[Path]
    apply_changes: bool
    duration_sec: float


def iter_source_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file())


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


def process_file(path: Path, apply_changes: bool) -> bool:
    original = path.read_text(encoding="utf-8", errors="ignore")
    lines = original.splitlines(keepends=True)
    header, body = split_header(lines)
    new_header, changed = transform_header(header)
    if not changed:
        return False

    if apply_changes:
        path.write_text("".join(new_header + body), encoding="utf-8", newline="")
    return True


def run_once(
    root: Path,
    apply_changes: bool,
    on_log: callable | None = None,
    on_progress: callable | None = None,
    labels: dict[str, str] | None = None,
) -> RunReport:
    labels = labels or DEFAULT_LABELS
    files = iter_source_files(root)
    total = len(files)
    changed_files: list[Path] = []
    mode = labels["apply_mode"] if apply_changes else labels["check_mode"]
    action = labels["updated"] if apply_changes else labels["would_update"]
    start = time.perf_counter()

    def log(msg: str) -> None:
        if on_log is None:
            print(msg)
        else:
            on_log(msg)

    log(f"[{mode}] {labels['root']}: {root.resolve()}")
    log(f"[{mode}] {labels['scanned']}: {total}")

    for idx, path in enumerate(files, start=1):
        if process_file(path, apply_changes=apply_changes):
            changed_files.append(path)
            log(path.as_posix())
        if on_progress is not None:
            on_progress(idx, total)

    log(f"[{mode}] {action} {len(changed_files)} {labels['files']}")
    duration = time.perf_counter() - start
    return RunReport(
        root=root,
        total_files=total,
        changed_files=changed_files,
        apply_changes=apply_changes,
        duration_sec=duration,
    )


def launch_gui() -> None:
    import tkinter as tk
    from tkinter import filedialog, font as tkfont, messagebox, scrolledtext, ttk

    class GuiApp:
        def __init__(self) -> None:
            self.root = tk.Tk()
            self.root.title("RTL 头注释处理工具")
            self.root.geometry("820x560")
            self.root.minsize(720, 520)
            self.root.configure(bg="#f4f2ee")

            default_font = tkfont.nametofont("TkDefaultFont")
            default_font.configure(family="Microsoft YaHei", size=10)
            self.root.option_add("*Font", default_font)

            style = ttk.Style(self.root)
            style.theme_use("clam")
            style.configure("TButton", padding=(10, 6))
            style.configure("TCheckbutton", padding=(6, 4))
            style.configure("TLabel", background="#f4f2ee")
            style.configure("Header.TLabel", font=("Microsoft YaHei", 14, "bold"))

            self.queue: queue.Queue[tuple[str, object]] = queue.Queue()
            self.worker_thread: threading.Thread | None = None
            self.apply_mode = tk.BooleanVar(value=True)
            self.verify_mode = tk.BooleanVar(value=True)
            self.dir_var = tk.StringVar(value=str(Path("rtl").resolve()))
            self.progress_var = tk.IntVar(value=0)
            self.progress_total = 0
            self.status_var = tk.StringVar(value="空闲。")

            self._build_ui()
            self.root.after(100, self._poll_queue)

        def _build_ui(self) -> None:
            header = tk.Frame(self.root, bg="#f4f2ee")
            header.pack(fill=tk.X, pady=(10, 0))
            ttk.Label(header, text="RTL 头注释处理工具", style="Header.TLabel").pack(anchor=tk.W, padx=12)
            tk.Label(header, text="支持目录选择、确认、进度显示、日志与报告", bg="#f4f2ee").pack(
                anchor=tk.W, padx=12, pady=(2, 6)
            )

            top = ttk.Frame(self.root, padding=10)
            top.pack(fill=tk.X)

            ttk.Label(top, text="目标目录：").pack(side=tk.LEFT)
            entry = ttk.Entry(top, textvariable=self.dir_var)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            ttk.Button(top, text="浏览…", command=self._browse).pack(side=tk.LEFT)

            options = ttk.Frame(self.root, padding=10)
            options.pack(fill=tk.X)
            ttk.Checkbutton(options, text="写回修改", variable=self.apply_mode).pack(side=tk.LEFT)
            ttk.Checkbutton(options, text="写回后复测", variable=self.verify_mode).pack(side=tk.LEFT, padx=12)
            ttk.Button(options, text="开始", command=self._start).pack(side=tk.RIGHT)

            progress_frame = ttk.Frame(self.root, padding=10)
            progress_frame.pack(fill=tk.X)
            self.progress = ttk.Progressbar(progress_frame, maximum=100)
            self.progress.pack(fill=tk.X)
            ttk.Label(progress_frame, textvariable=self.status_var).pack(anchor=tk.W, pady=6)

            log_frame = ttk.Frame(self.root, padding=10)
            log_frame.pack(fill=tk.BOTH, expand=True)
            self.log_widget = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=16)
            self.log_widget.pack(fill=tk.BOTH, expand=True)
            self.log_widget.configure(state=tk.DISABLED)

        def _browse(self) -> None:
            directory = filedialog.askdirectory(initialdir=self.dir_var.get())
            if directory:
                self.dir_var.set(directory)

        def _start(self) -> None:
            if self.worker_thread and self.worker_thread.is_alive():
                return
            target = Path(self.dir_var.get())
            if not target.exists() or not target.is_dir():
                messagebox.showerror("目录无效", "请选择有效的目录。")
                return
            if not self.apply_mode.get():
                self.verify_mode.set(False)
            mode_label = "写回修改" if self.apply_mode.get() else "仅检查"
            confirm = messagebox.askyesno(
                "确认",
                f"目标目录：{target}\n模式：{mode_label}\n\n是否继续？",
            )
            if not confirm:
                self._log("用户已取消。")
                return
            self._set_running(True)
            self.progress_var.set(0)
            self.progress_total = 0
            self.status_var.set("开始处理...")
            self._log("------------------------------------------------------------")
            self._log(f"目标目录：{target}")
            self._log(f"处理模式：{mode_label}")
            self._log("------------------------------------------------------------")
            self.worker_thread = threading.Thread(target=self._run_worker, args=(target,), daemon=True)
            self.worker_thread.start()

        def _run_worker(self, target: Path) -> None:
            try:
                self.queue.put(("phase", "apply" if self.apply_mode.get() else "check"))
                report_apply = run_once(
                    target,
                    apply_changes=self.apply_mode.get(),
                    on_log=lambda msg: self.queue.put(("log", msg)),
                    on_progress=lambda i, t: self.queue.put(("progress", (i, t))),
                    labels=CHINESE_LABELS,
                )
                report_check = None
                if self.apply_mode.get() and self.verify_mode.get():
                    self.queue.put(("phase", "verify"))
                    report_check = run_once(
                        target,
                        apply_changes=False,
                        on_log=lambda msg: self.queue.put(("log", msg)),
                        on_progress=lambda i, t: self.queue.put(("progress", (i, t))),
                        labels=CHINESE_LABELS,
                    )
                self.queue.put(("done", (report_apply, report_check)))
            except Exception as exc:  # pragma: no cover - GUI only
                self.queue.put(("error", str(exc)))

        def _poll_queue(self) -> None:
            try:
                while True:
                    event, payload = self.queue.get_nowait()
                    if event == "log":
                        self._log(str(payload))
                    elif event == "progress":
                        current, total = payload
                        if total > 0:
                            self.progress_total = total
                            self.progress.configure(maximum=total)
                            self.progress_var.set(current)
                            self.progress.configure(value=current)
                        self.status_var.set(f"正在处理 {current}/{total} 个文件...")
                    elif event == "phase":
                        phase = payload
                        self.progress_var.set(0)
                        if phase == "verify":
                            self.status_var.set("复测中...")
                        else:
                            self.status_var.set("正在处理文件...")
                    elif event == "done":
                        report_apply, report_check = payload
                        self._finish(report_apply, report_check)
                    elif event == "error":
                        self._log(f"[ERROR] {payload}")
                        messagebox.showerror("Error", str(payload))
                        self._set_running(False)
            except queue.Empty:
                pass
            self.root.after(100, self._poll_queue)

        def _finish(self, report_apply: RunReport, report_check: RunReport | None) -> None:
            summary_lines = [
                "------------------------------------------------------------",
                "处理报告",
                f"目标目录：{report_apply.root}",
                f"处理模式：{'写回' if report_apply.apply_changes else '检查'}",
                f"扫描文件数：{report_apply.total_files}",
                f"命中文件数：{len(report_apply.changed_files)}",
                f"耗时：{report_apply.duration_sec:.2f}s",
            ]
            if report_check is not None:
                summary_lines.extend(
                    [
                        "复测结果：",
                        f"命中文件数：{len(report_check.changed_files)}",
                        f"耗时：{report_check.duration_sec:.2f}s",
                    ]
                )
            summary_lines.append("------------------------------------------------------------")
            for line in summary_lines:
                self._log(line)
            messagebox.showinfo("处理报告", "\n".join(summary_lines))
            self.status_var.set("处理完成。")
            self._set_running(False)

        def _log(self, msg: str) -> None:
            self.log_widget.configure(state=tk.NORMAL)
            self.log_widget.insert(tk.END, msg + "\n")
            self.log_widget.see(tk.END)
            self.log_widget.configure(state=tk.DISABLED)

        def _set_running(self, running: bool) -> None:
            for child in self.root.winfo_children():
                for widget in child.winfo_children():
                    if isinstance(widget, ttk.Button) or isinstance(widget, ttk.Checkbutton) or isinstance(widget, ttk.Entry):
                        widget.configure(state=tk.DISABLED if running else tk.NORMAL)

        def run(self) -> None:
            self.root.mainloop()

    GuiApp().run()


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize RTL file headers.")
    parser.add_argument("root", nargs="?", default="rtl", help="Root directory to process.")
    parser.add_argument("--apply", action="store_true", help="Write changes in place.")
    parser.add_argument("--gui", action="store_true", help="Launch GUI.")
    args = parser.parse_args()

    if args.gui:
        launch_gui()
        return 0

    root = Path(args.root)
    run_once(root, apply_changes=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
