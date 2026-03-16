import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText


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


def is_probably_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\x00" in data:
        return True
    # Heuristic: too many control chars may indicate binary
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


def decode_with_candidates(data: bytes):
    for enc in ENCODING_CANDIDATES:
        try:
            text = data.decode(enc)
        except UnicodeDecodeError:
            continue
        return text, enc
    return None, None


def is_text_extension(path: str) -> bool:
    _, ext = os.path.splitext(path)
    if not ext:
        return True
    return ext.lower() in TEXT_EXTENSIONS


class Utf8ConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("文本转 UTF-8 工具")
        self.root.geometry("860x560")
        self.root.minsize(780, 520)

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
            text="文本编码自动转换为 UTF-8",
            font=("Segoe UI", 16, "bold"),
        )
        title.pack(pady=(16, 6))

        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.X)

        self.dir_var = tk.StringVar()
        dir_label = ttk.Label(frame, text="目标目录：")
        dir_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 6))

        dir_entry = ttk.Entry(frame, textvariable=self.dir_var)
        dir_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 6))

        browse_btn = ttk.Button(frame, text="选择目录", command=self._select_dir)
        browse_btn.grid(row=0, column=2)

        frame.columnconfigure(1, weight=1)

        options = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        options.pack(fill=tk.X)
        self.include_no_ext = tk.BooleanVar(value=True)
        check = ttk.Checkbutton(
            options,
            text="包含无后缀文件（若为文本）",
            variable=self.include_no_ext
        )
        check.pack(anchor=tk.W)

        control = ttk.Frame(self.root, padding=(12, 0, 12, 8))
        control.pack(fill=tk.X)
        self.start_btn = ttk.Button(control, text="开始转换", command=self._start)
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

    def _select_dir(self):
        path = filedialog.askdirectory()
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

        confirm = messagebox.askokcancel(
            "确认转换",
            "将递归扫描目录并直接修改文件编码为 UTF-8。\n"
            "此操作不可自动撤销，是否继续？"
        )
        if not confirm:
            return

        self._reset_ui()
        self.running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.worker_thread = threading.Thread(
            target=self._worker,
            args=(root_dir, self.include_no_ext.get()),
            daemon=True
        )
        self.worker_thread.start()

    def _reset_ui(self):
        self.progress["value"] = 0
        self.progress_label.configure(text="准备中...")
        self._append_log("开始扫描并转换...\n")

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

    def _worker(self, root_dir: str, include_no_ext: bool):
        stats = {
            "total": 0,
            "processed": 0,
            "converted": 0,
            "utf8": 0,
            "no_chinese": 0,
            "binary": 0,
            "decode_fail": 0,
            "skipped_ext": 0,
        }

        all_files = []
        for base, _, files in os.walk(root_dir):
            for name in files:
                path = os.path.join(base, name)
                if not is_text_extension(path):
                    stats["skipped_ext"] += 1
                    continue
                if not include_no_ext:
                    _, ext = os.path.splitext(path)
                    if not ext:
                        stats["skipped_ext"] += 1
                        continue
                all_files.append(path)

        stats["total"] = len(all_files)
        self.progress_queue.put((0, stats["total"], "开始处理"))
        self.log_queue.put(f"扫描到候选文件数：{stats['total']}\n")

        for idx, path in enumerate(all_files, start=1):
            stats["processed"] += 1
            self.progress_queue.put((idx, stats["total"], "处理中"))
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError as exc:
                self.log_queue.put(f"[读取失败] {path} ({exc})\n")
                continue

            if is_probably_binary(data):
                stats["binary"] += 1
                self.log_queue.put(f"[跳过-疑似二进制] {path}\n")
                continue

            try:
                text = data.decode("utf-8")
                if contains_chinese(text):
                    stats["utf8"] += 1
                    self.log_queue.put(f"[已是UTF-8] {path}\n")
                else:
                    stats["no_chinese"] += 1
                    self.log_queue.put(f"[无中文] {path}\n")
                continue
            except UnicodeDecodeError:
                pass

            text, enc = decode_with_candidates(data)
            if text is None:
                stats["decode_fail"] += 1
                self.log_queue.put(f"[解码失败] {path}\n")
                continue

            if not contains_chinese(text):
                stats["no_chinese"] += 1
                self.log_queue.put(f"[无中文-跳过] {path} (原编码: {enc})\n")
                continue

            try:
                with open(path, "wb") as f:
                    f.write(text.encode("utf-8"))
                stats["converted"] += 1
                self.log_queue.put(f"[已转换] {path} (原编码: {enc})\n")
            except OSError as exc:
                self.log_queue.put(f"[写入失败] {path} ({exc})\n")

        summary = (
            "\n处理完成\n"
            f"总候选文件: {stats['total']}\n"
            f"已处理文件: {stats['processed']}\n"
            f"已转换UTF-8: {stats['converted']}\n"
            f"已是UTF-8: {stats['utf8']}\n"
            f"无中文跳过: {stats['no_chinese']}\n"
            f"疑似二进制跳过: {stats['binary']}\n"
            f"解码失败: {stats['decode_fail']}\n"
            f"扩展名跳过: {stats['skipped_ext']}\n"
        )
        self.log_queue.put(summary)
        self.progress_queue.put((stats["total"], stats["total"], "完成"))

        self.root.after(0, self._finish)

    def _finish(self):
        self.running = False
        self.start_btn.configure(state=tk.NORMAL)
        messagebox.showinfo("完成", "转换完成，详情请查看日志。")


def main():
    root = tk.Tk()
    app = Utf8ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
