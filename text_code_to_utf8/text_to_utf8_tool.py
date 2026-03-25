import os
import queue
import shutil
import threading
import tkinter as tk
import unicodedata
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


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
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".csv", ".tsv", ".c", ".h", ".cpp", ".hpp", ".cc", ".cxx",
    ".java", ".py", ".js", ".ts", ".go", ".rs", ".v", ".sv", ".vh", ".vhd", ".vhdl",
    ".scala", ".sc", ".sbt", ".tcl", ".sh", ".bat", ".ps1", ".json", ".yaml", ".yml",
    ".ini", ".cfg", ".toml", ".xml", ".html", ".htm", ".css", ".scss", ".less", ".sql",
    ".lua", ".mk", ".cmake", ".make", ".gradle", ".properties", ".gitignore", ".gitattributes",
}
LEGACY_CANDIDATES = ["gb18030", "gbk", "gb2312", "big5"]
TARGET_LABELS = {"utf-8": "UTF-8", "gb2312": "GB2312"}
BOM_ENCODINGS = [
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe\x00\x00", "utf-32"),
    (b"\x00\x00\xfe\xff", "utf-32"),
    (b"\xff\xfe", "utf-16"),
    (b"\xfe\xff", "utf-16"),
]


@dataclass
class ConversionOptions:
    mode: str
    target_path: str
    target_encoding: str = "utf-8"
    include_no_ext: bool = True
    create_backup: bool = False


@dataclass
class ConversionStats:
    total: int = 0
    processed: int = 0
    converted: int = 0
    utf8: int = 0
    utf8_bom: int = 0
    no_chinese: int = 0
    binary: int = 0
    decode_fail: int = 0
    encode_fail: int = 0
    skipped_ext: int = 0
    read_fail: int = 0
    write_fail: int = 0
    backups: int = 0
    cancelled: bool = False

    def snapshot(self):
        return {
            "total": self.total,
            "processed": self.processed,
            "converted": self.converted,
            "utf8": self.utf8 + self.utf8_bom,
            "skipped": self.no_chinese + self.binary + self.skipped_ext,
            "failures": self.decode_fail + self.encode_fail + self.read_fail + self.write_fail,
            "backups": self.backups,
        }

    def popup_summary(self, target_label):
        title = "已取消" if self.cancelled else "已完成"
        return (
            f"{title}\n\n总候选: {self.total}\n已处理: {self.processed}\n已转换: {self.converted}\n"
            f"已是{target_label}: {self.utf8 + self.utf8_bom}\n跳过: {self.no_chinese + self.binary + self.skipped_ext}\n"
            f"失败: {self.decode_fail + self.encode_fail + self.read_fail + self.write_fail}\n备份: {self.backups}"
        )


def count_chinese(text):
    total = 0
    for ch in text:
        code = ord(ch)
        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF:
            total += 1
    return total


def get_target_label(target_encoding):
    return TARGET_LABELS.get(target_encoding, target_encoding.upper())


def detect_bom_encoding(data):
    for signature, encoding in BOM_ENCODINGS:
        if data.startswith(signature):
            return encoding
    return None


def guess_utf16_encoding(data):
    if len(data) < 8 or len(data) % 2 != 0:
        return None
    sample = data[: min(len(data), 4096)]
    pairs = max(len(sample) // 2, 1)
    even_zero = sum(1 for i in range(0, len(sample), 2) if sample[i] == 0)
    odd_zero = sum(1 for i in range(1, len(sample), 2) if sample[i] == 0)
    if odd_zero / pairs > 0.30 and even_zero / pairs < 0.08:
        return "utf-16-le"
    if even_zero / pairs > 0.30 and odd_zero / pairs < 0.08:
        return "utf-16-be"
    return None


def is_probably_binary(data):
    if not data:
        return False
    if detect_bom_encoding(data) or guess_utf16_encoding(data):
        return False
    if b"\x00" in data:
        return True
    # Raw-byte heuristic / 原始字节启发式判定
    ctrl = sum(1 for value in data if value < 9 or (13 < value < 32))
    return (ctrl / max(len(data), 1)) > 0.3


def score_text_quality(text):
    if not text:
        return 1000.0, 1.0, 0.0
    printable = 0
    control = 0
    unusual = 0
    for ch in text:
        if ch in "\r\n\t":
            printable += 1
            continue
        category = unicodedata.category(ch)
        if category.startswith("C"):
            control += 1
            continue
        if ch.isprintable():
            printable += 1
        else:
            unusual += 1
    length = max(len(text), 1)
    printable_ratio = printable / length
    control_ratio = control / length
    score = printable_ratio * 1000 - control_ratio * 2000 - unusual * 0.5
    score += min(count_chinese(text), 30) + min(text.count("\n"), 40) * 2
    return score, printable_ratio, control_ratio


def is_reasonable_text(text):
    score, printable_ratio, control_ratio = score_text_quality(text)
    if len(text) < 12:
        return control_ratio == 0
    return score > 860 and printable_ratio >= 0.92 and control_ratio <= 0.02


def decode_with_candidates(data):
    candidates = []
    guessed_utf16 = guess_utf16_encoding(data)
    if guessed_utf16:
        candidates.extend([guessed_utf16, "utf-16-be" if guessed_utf16 == "utf-16-le" else "utf-16-le"])
    for encoding in LEGACY_CANDIDATES:
        if encoding not in candidates:
            candidates.append(encoding)
    best = None
    for encoding in candidates:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if not is_reasonable_text(text):
            continue
        score, _, _ = score_text_quality(text)
        if best is None or score > best[0]:
            best = (score, text, encoding)
    if best is None:
        return None, None
    return best[1], best[2]


def decode_text_content(data):
    bom_encoding = detect_bom_encoding(data)
    if bom_encoding:
        try:
            text = data.decode(bom_encoding)
        except UnicodeDecodeError:
            return None, None
        if is_reasonable_text(text):
            return text, bom_encoding
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    else:
        if is_reasonable_text(text):
            return text, "utf-8"
    return decode_with_candidates(data)


def detect_target_status(data, text, target_encoding):
    if target_encoding == "utf-8":
        try:
            if data.decode("utf-8") == text:
                return "exact"
        except UnicodeDecodeError:
            pass
        try:
            if data.decode("utf-8-sig") == text:
                return "bom"
        except UnicodeDecodeError:
            pass
        return None
    try:
        decoded = data.decode(target_encoding)
    except UnicodeError:
        return None
    try:
        if decoded == text and decoded.encode(target_encoding) == data:
            return "exact"
    except UnicodeError:
        return None
    return None


def encode_text_for_target(text, target_encoding):
    return text.encode(target_encoding)


def build_backup_path(path):
    candidate = f"{path}.bak"
    if not os.path.exists(candidate):
        return candidate
    index = 1
    while True:
        candidate = f"{path}.bak{index}"
        if not os.path.exists(candidate):
            return candidate
        index += 1


def collect_targets(options, stats):
    if options.mode == "file":
        return [options.target_path]
    targets = []
    for base, dir_names, file_names in os.walk(options.target_path):
        # Stable ordering for repeatable logs / 稳定排序便于复现实验
        dir_names.sort()
        for name in sorted(file_names):
            path = os.path.join(base, name)
            _, ext = os.path.splitext(path)
            if not ext and not options.include_no_ext:
                stats.skipped_ext += 1
                continue
            if ext and ext.lower() not in TEXT_EXTENSIONS:
                stats.skipped_ext += 1
                continue
            targets.append(path)
    return targets


def format_summary(stats, options):
    scope = "单文件" if options.mode == "file" else "目录递归"
    title = "处理已取消" if stats.cancelled else "处理完成"
    target_label = get_target_label(options.target_encoding)
    bom_line = f"已是{target_label}(BOM): {stats.utf8_bom}\n" if options.target_encoding == "utf-8" else ""
    return (
        f"\n{title}\n处理模式: {scope}\n目标路径: {options.target_path}\n总候选文件: {stats.total}\n"
        f"目标编码: {target_label}\n已处理文件: {stats.processed}\n已转换: {stats.converted}\n已是{target_label}: {stats.utf8}\n"
        f"{bom_line}无中文跳过: {stats.no_chinese}\n疑似二进制跳过: {stats.binary}\n"
        f"扩展名跳过: {stats.skipped_ext}\n读取失败: {stats.read_fail}\n写入失败: {stats.write_fail}\n"
        f"解码失败: {stats.decode_fail}\n目标编码不支持: {stats.encode_fail}\n已创建备份: {stats.backups}\n"
    )


def process_one_file(path, options, stats, log_callback):
    try:
        with open(path, "rb") as file_obj:
            data = file_obj.read()
    except OSError as exc:
        stats.read_fail += 1
        log_callback(f"[读取失败] {path} ({exc})\n")
        return
    if is_probably_binary(data):
        stats.binary += 1
        log_callback(f"[跳过-疑似二进制] {path}\n")
        return
    text, encoding = decode_text_content(data)
    if text is None or encoding is None:
        stats.decode_fail += 1
        log_callback(f"[解码失败] {path}\n")
        return
    if count_chinese(text) == 0:
        stats.no_chinese += 1
        log_callback(f"[无中文-跳过] {path} (识别编码: {encoding})\n")
        return

    target_label = get_target_label(options.target_encoding)
    target_status = detect_target_status(data, text, options.target_encoding)
    if target_status == "exact":
        stats.utf8 += 1
        log_callback(f"[已是目标编码] {path} (目标编码: {target_label})\n")
        return
    if target_status == "bom":
        stats.utf8_bom += 1
        log_callback(f"[已是目标编码(BOM)] {path} (目标编码: {target_label})\n")
        return
    if options.create_backup:
        backup_path = build_backup_path(path)
        try:
            shutil.copy2(path, backup_path)
        except OSError as exc:
            stats.write_fail += 1
            log_callback(f"[备份失败-跳过] {path} ({exc})\n")
            return
        stats.backups += 1
        log_callback(f"[已备份] {backup_path}\n")
    try:
        with open(path, "wb") as file_obj:
            file_obj.write(encode_text_for_target(text, options.target_encoding))
    except UnicodeEncodeError as exc:
        stats.encode_fail += 1
        log_callback(f"[目标编码不支持-跳过] {path} (目标编码: {target_label}, {exc})\n")
        return
    except OSError as exc:
        stats.write_fail += 1
        log_callback(f"[写入失败] {path} ({exc})\n")
        return
    stats.converted += 1
    log_callback(f"[已转换] {path} (原编码: {encoding} -> 目标编码: {target_label})\n")


def process_targets(options, log_callback, progress_callback, stop_event):
    stats = ConversionStats()
    targets = collect_targets(options, stats)
    stats.total = len(targets)
    scope = "单文件" if options.mode == "file" else "目录递归"
    target_label = get_target_label(options.target_encoding)
    log_callback(f"处理模式：{scope}\n目标路径：{options.target_path}\n")
    log_callback(f"目标编码：{target_label}\n")
    log_callback(f"转换前备份：{'是' if options.create_backup else '否'}\n")
    if options.mode == "directory":
        log_callback(f"包含无后缀文件：{'是' if options.include_no_ext else '否'}\n")
    log_callback("开始扫描并转换...\n")
    progress_callback(0, stats.total, "准备完成", stats.snapshot())
    if stats.total == 0:
        log_callback("未找到需要处理的候选文件。\n")
        log_callback(format_summary(stats, options))
        progress_callback(0, 0, "无候选文件", stats.snapshot())
        return stats
    for index, path in enumerate(targets, start=1):
        if stop_event.is_set():
            stats.cancelled = True
            log_callback("\n收到停止请求，已提前结束当前任务。\n")
            break
        progress_callback(index - 1, stats.total, f"处理中: {os.path.basename(path)}", stats.snapshot())
        stats.processed += 1
        process_one_file(path, options, stats, log_callback)
        progress_callback(index, stats.total, f"已处理 {stats.processed}/{stats.total}", stats.snapshot())
    log_callback(format_summary(stats, options))
    progress_callback(stats.processed, stats.total, "已取消" if stats.cancelled else "完成", stats.snapshot())
    return stats


class Utf8ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Text Code Converter")
        self.root.geometry("1020x730")
        self.root.minsize(900, 650)
        self.root.configure(bg=THEME["bg"])
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.finish_queue = queue.Queue()
        self.stop_event = threading.Event()
        self.worker_thread = None
        self.running = False
        self.mode_var = tk.StringVar(value="directory")
        self.path_var = tk.StringVar()
        self.path_label_var = tk.StringVar(value="目标目录")
        self.path_hint_var = tk.StringVar(value="递归扫描所选目录及全部子目录中的文本文件。")
        self.browse_text_var = tk.StringVar(value="选择目录")
        self.progress_text_var = tk.StringVar(value="等待开始")
        self.metric_note_var = tk.StringVar(value="跳过: 0 | 备份: 0")
        self.target_encoding = tk.StringVar(value="utf-8")
        self.active_target_encoding = "utf-8"
        self.include_no_ext = tk.BooleanVar(value=True)
        self.create_backup = tk.BooleanVar(value=False)
        self.metric_vars = {name: tk.StringVar(value="0") for name in ["total", "processed", "converted", "utf8", "failures"]}
        self._setup_styles()
        self._build_ui()
        self._on_mode_change()
        self._poll_queues()

    def _setup_styles(self):
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
        style.map("Accent.TButton", background=[("active", THEME["accent_dark"]), ("disabled", "#8db5b0")], foreground=[("disabled", "#edf8f6")])
        style.configure("Soft.TButton", background="#e5edf5", foreground=THEME["text"], borderwidth=0, padding=(12, 8), font=(FONT_NAME, 10))
        style.map("Soft.TButton", background=[("active", "#d6e1ec"), ("disabled", "#eff4f8")], foreground=[("disabled", "#92a0b1")])
        style.configure("Modern.TEntry", fieldbackground="#f8fbfe", foreground=THEME["text"], bordercolor=THEME["border"], lightcolor=THEME["border"], darkcolor=THEME["border"], padding=8)
        style.configure("Modern.TRadiobutton", background=THEME["surface"], foreground=THEME["text"], font=(FONT_NAME, 10))
        style.configure("Modern.TCheckbutton", background=THEME["surface"], foreground=THEME["text"], font=(FONT_NAME, 10))
        style.configure("Modern.Horizontal.TProgressbar", troughcolor=THEME["progress"], background=THEME["accent"], bordercolor=THEME["progress"], lightcolor=THEME["accent"], darkcolor=THEME["accent"], thickness=12)
        style.configure("MetricValue.TLabel", background=THEME["surface"], foreground=THEME["accent_dark"], font=(FONT_NAME, 18, "bold"))
        style.configure("MetricKey.TLabel", background=THEME["surface"], foreground=THEME["muted"], font=(FONT_NAME, 9))

    def _build_ui(self):
        container = ttk.Frame(self.root, style="App.TFrame", padding=18)
        container.pack(fill=tk.BOTH, expand=True)
        hero = ttk.Frame(container, style="Hero.TFrame", padding=(22, 20))
        hero.pack(fill=tk.X)
        ttk.Label(hero, text="TEXT CODE CONVERTER", style="HeroSmall.TLabel").pack(anchor=tk.W)
        ttk.Label(hero, text="文本编码整理工作台", style="HeroTitle.TLabel").pack(anchor=tk.W, pady=(6, 4))
        ttk.Label(hero, text="支持目录递归与单文件处理，可输出 UTF-8 或 GB2312，并实时反馈日志。", style="HeroText.TLabel").pack(anchor=tk.W)
        body = ttk.Frame(container, style="App.TFrame")
        body.pack(fill=tk.BOTH, expand=True, pady=(16, 0))
        body.columnconfigure(0, weight=7)
        body.columnconfigure(1, weight=4)
        body.rowconfigure(2, weight=1)
        target = self._make_card(body, 0, 0, "处理目标", "选择扫描方式，并指定需要处理的文件或目录。")
        target.columnconfigure(1, weight=1)
        mode_row = ttk.Frame(target, style="Card.TFrame")
        mode_row.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(8, 12))
        ttk.Radiobutton(mode_row, text="目录递归", value="directory", variable=self.mode_var, command=self._on_mode_change, style="Modern.TRadiobutton").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_row, text="单文件", value="file", variable=self.mode_var, command=self._on_mode_change, style="Modern.TRadiobutton").pack(side=tk.LEFT, padx=(18, 0))
        ttk.Label(target, textvariable=self.path_label_var, style="Body.TLabel").grid(row=3, column=0, sticky="w", padx=(0, 10))
        self.path_entry = ttk.Entry(target, textvariable=self.path_var, style="Modern.TEntry")
        self.path_entry.grid(row=3, column=1, sticky="ew", padx=(0, 10))
        ttk.Button(target, textvariable=self.browse_text_var, style="Soft.TButton", command=self._browse_target).grid(row=3, column=2, sticky="e")
        ttk.Label(target, textvariable=self.path_hint_var, style="Hint.TLabel").grid(row=4, column=0, columnspan=3, sticky="w", pady=(10, 0))
        control = self._make_card(body, 1, 0, "执行控制", "开始前会弹出确认框，可在处理中请求停止。")
        control.columnconfigure(0, weight=1)
        self.start_btn = ttk.Button(control, text="开始转换", style="Accent.TButton", command=self._start)
        self.start_btn.grid(row=2, column=0, sticky="w", pady=(8, 12))
        self.stop_btn = ttk.Button(control, text="停止任务", style="Soft.TButton", command=self._stop)
        self.stop_btn.grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(8, 12))
        self.stop_btn.configure(state=tk.DISABLED)
        self.progress = ttk.Progressbar(control, mode="determinate", style="Modern.Horizontal.TProgressbar")
        self.progress.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Label(control, textvariable=self.progress_text_var, style="Hint.TLabel").grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))
        log_card = self._make_card(body, 2, 0, "详细日志", "逐项输出处理结果，便于追踪每个文件。", fill=True)
        log_card.rowconfigure(3, weight=1)
        log_card.columnconfigure(0, weight=1)
        header = ttk.Frame(log_card, style="Card.TFrame")
        header.grid(row=2, column=0, sticky="ew", pady=(8, 10))
        ttk.Label(header, text="实时处理日志", style="Body.TLabel").pack(side=tk.LEFT)
        ttk.Button(header, text="清空日志", style="Soft.TButton", command=self._clear_log).pack(side=tk.RIGHT)
        self.log_text = ScrolledText(log_card, height=18, wrap=tk.WORD, font=(LOG_FONT, 10), background=THEME["log_bg"], foreground=THEME["text"], insertbackground=THEME["text"], relief=tk.FLAT, highlightthickness=1, highlightbackground=THEME["border"], padx=12, pady=10)
        self.log_text.grid(row=3, column=0, sticky="nsew")
        self.log_text.configure(state=tk.DISABLED)
        options = self._make_card(body, 0, 1, "处理选项", "选择目标编码，并按需开启额外安全措施。")
        ttk.Label(options, text="目标编码", style="Body.TLabel").grid(row=2, column=0, sticky="w", pady=(8, 6))
        target_row = ttk.Frame(options, style="Card.TFrame")
        target_row.grid(row=3, column=0, sticky="w")
        ttk.Radiobutton(target_row, text="UTF-8", value="utf-8", variable=self.target_encoding, style="Modern.TRadiobutton").pack(side=tk.LEFT)
        ttk.Radiobutton(target_row, text="GB2312", value="gb2312", variable=self.target_encoding, style="Modern.TRadiobutton").pack(side=tk.LEFT, padx=(18, 0))
        self.include_no_ext_check = ttk.Checkbutton(options, text="目录模式包含无后缀文件", variable=self.include_no_ext, style="Modern.TCheckbutton")
        self.include_no_ext_check.grid(row=4, column=0, sticky="w", pady=(10, 8))
        ttk.Checkbutton(options, text="转换前创建 .bak 备份", variable=self.create_backup, style="Modern.TCheckbutton").grid(row=5, column=0, sticky="w")
        ttk.Label(options, text="单文件模式下不做扩展名过滤，但仍会做二进制、解码和目标编码判定。", style="Hint.TLabel").grid(row=6, column=0, sticky="w", pady=(10, 0))
        summary = self._make_card(body, 1, 1, "结果概览", "执行过程中持续刷新关键统计。")
        metrics = [("总候选", "total"), ("已处理", "processed"), ("已转换", "converted"), ("已是目标编码", "utf8"), ("失败数", "failures")]
        for index, (label, key) in enumerate(metrics):
            block = ttk.Frame(summary, style="Card.TFrame")
            block.grid(row=2 + index // 2, column=index % 2, sticky="w", padx=(0, 16), pady=(10 if index < 2 else 12, 0))
            ttk.Label(block, text=label, style="MetricKey.TLabel").pack(anchor=tk.W)
            ttk.Label(block, textvariable=self.metric_vars[key], style="MetricValue.TLabel").pack(anchor=tk.W)
        ttk.Label(summary, textvariable=self.metric_note_var, style="Hint.TLabel").grid(row=5, column=0, columnspan=2, sticky="w", pady=(14, 0))
        hint = self._make_card(body, 2, 1, "识别增强", "本版增加了编码识别、目标编码和误判抑制。", fill=True)
        ttk.Label(hint, text="支持点：\n1. UTF-8 / GB2312 目标编码单选\n2. UTF-8 / UTF-8 BOM 识别\n3. UTF-16 / UTF-32 BOM 识别\n4. 无 BOM 的 UTF-16 启发式判断\n5. GB18030 / GBK / GB2312 / Big5 候选解码\n6. 停止任务、备份与更清晰的结果汇总", style="Body.TLabel", justify=tk.LEFT).grid(row=2, column=0, sticky="nw", pady=(8, 0))

    def _make_card(self, parent, row, column, title, subtitle, fill=False):
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        sticky = "nsew" if fill else "ew"
        card.grid(row=row, column=column, sticky=sticky, padx=(0, 14 if column == 0 else 0), pady=(0, 14))
        ttk.Label(card, text=title, style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, text=subtitle, style="Hint.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        return card

    def _on_mode_change(self):
        if self.mode_var.get() == "file":
            self.path_label_var.set("目标文件")
            self.path_hint_var.set("仅处理一个文件，适合先试运行或单独修复某个文件。")
            self.browse_text_var.set("选择文件")
            self.include_no_ext_check.state(["disabled"])
        else:
            self.path_label_var.set("目标目录")
            self.path_hint_var.set("递归扫描所选目录及全部子目录中的文本文件。")
            self.browse_text_var.set("选择目录")
            self.include_no_ext_check.state(["!disabled"])

    def _browse_target(self):
        path = filedialog.askopenfilename() if self.mode_var.get() == "file" else filedialog.askdirectory()
        if path:
            self.path_var.set(path)

    def _clear_log(self):
        if self.running:
            return
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _append_log(self, text):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, text)
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
        print(text, end="")

    def _update_metrics(self, snapshot):
        for key in self.metric_vars:
            self.metric_vars[key].set(str(snapshot.get(key, 0)))
        self.metric_note_var.set(f"跳过: {snapshot.get('skipped', 0)} | 备份: {snapshot.get('backups', 0)}")

    def _start(self):
        if self.running:
            return
        target_path = self.path_var.get().strip()
        mode = self.mode_var.get()
        target_label = get_target_label(self.target_encoding.get())
        if not target_path:
            messagebox.showwarning("提示", "请先选择目标文件或目录。")
            return
        if mode == "file":
            if not os.path.isfile(target_path):
                messagebox.showerror("错误", "选择的文件不存在。")
                return
            confirm = f"将直接处理当前选中的单个文件。\n若检测到文件含中文且编码不是目标编码，将覆盖写回为 {target_label}。\n此操作不可自动撤销，是否继续？"
        else:
            if not os.path.isdir(target_path):
                messagebox.showerror("错误", "选择的目录不存在。")
                return
            confirm = f"将递归扫描目录及全部子目录，并直接修改符合条件的文件为 {target_label}。\n此操作不可自动撤销，是否继续？"
        if not messagebox.askokcancel("确认转换", confirm):
            return
        options = ConversionOptions(mode, target_path, self.target_encoding.get(), self.include_no_ext.get(), self.create_backup.get())
        self.active_target_encoding = options.target_encoding
        self._clear_log()
        self._update_metrics(ConversionStats().snapshot())
        self.progress["value"] = 0
        self.progress_text_var.set("准备中...")
        self.stop_event.clear()
        self.running = True
        self.start_btn.configure(state=tk.DISABLED)
        self.stop_btn.configure(state=tk.NORMAL)
        self.worker_thread = threading.Thread(target=self._worker, args=(options,), daemon=True)
        self.worker_thread.start()

    def _stop(self):
        if not self.running:
            return
        self.stop_event.set()
        self.progress_text_var.set("停止请求已发送，等待当前文件处理结束...")
        self.stop_btn.configure(state=tk.DISABLED)

    def _worker(self, options):
        try:
            stats = process_targets(options, self.log_queue.put, lambda value, total, status, snapshot: self.progress_queue.put((value, total, status, snapshot)), self.stop_event)
        except Exception as exc:  # Defensive fallback / 防御性兜底
            stats = ConversionStats(write_fail=1)
            self.log_queue.put(f"[内部错误] {exc}\n")
        self.finish_queue.put(stats)

    def _poll_queues(self):
        try:
            while True:
                self._append_log(self.log_queue.get_nowait())
        except queue.Empty:
            pass
        try:
            while True:
                value, total, status, snapshot = self.progress_queue.get_nowait()
                self.progress["maximum"] = max(total, 1)
                self.progress["value"] = min(value, max(total, 1))
                self.progress_text_var.set(status)
                self._update_metrics(snapshot)
        except queue.Empty:
            pass
        try:
            while True:
                self._finish(self.finish_queue.get_nowait())
        except queue.Empty:
            pass
        self.root.after(120, self._poll_queues)

    def _finish(self, stats):
        self.running = False
        self.start_btn.configure(state=tk.NORMAL)
        self.stop_btn.configure(state=tk.DISABLED)
        messagebox.showinfo("任务已取消" if stats.cancelled else "转换完成", stats.popup_summary(get_target_label(self.active_target_encoding)))

    def _on_close(self):
        if self.running:
            confirm = messagebox.askokcancel("确认退出", "当前任务仍在执行中，退出会立即结束程序。是否继续退出？")
            if not confirm:
                return
        self.root.destroy()


def main():
    root = tk.Tk()
    Utf8ConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
