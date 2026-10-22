# -*- coding: utf-8 -*-
"""图形界面（tkinter，随 Python 内置，无第三方依赖）。"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk
import tkinter as tk

from . import FILE_PATTERNS, SUPPORTED_EXTS, __version__
from .core import collect_inputs, convert_one, format_report
from .logging_util import log_line
from .office_com import detect_office

APP_TITLE = "Office 转 Markdown（离线版）"


def _dpi_aware() -> None:
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


class App:
    def __init__(self, root: Tk):
        self.root = root
        self.files: list[Path] = []
        self.queue: "queue.Queue[tuple]" = queue.Queue()
        self.running = False
        self.cancel_flag = threading.Event()

        root.title(f"{APP_TITLE}   v{__version__}")
        root.geometry("900x660")
        root.minsize(780, 580)
        self._build()
        self._log(f"就绪。支持格式：{'、'.join(sorted(SUPPORTED_EXTS))}")
        st = detect_office()
        self._log(
            "Office 检测：Word={word}  Excel={excel}  PowerPoint={powerpoint}  pywin32={pywin32}".format(**st)
        )
        if not st.get("pywin32"):
            self._log("提示：未检测到 pywin32，.doc/.ppt 将无法通过 Office 转换。")
        root.after(120, self._poll)

    # ---------------- UI ----------------
    def _build(self) -> None:
        try:
            ttk.Style().theme_use("vista")
        except Exception:
            pass
        self.root.option_add("*Font", ("Microsoft YaHei UI", 10))

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        box_in = ttk.LabelFrame(outer, text=" 1. 待转换文件 ", padding=8)
        box_in.pack(fill="both", expand=True)
        bar = ttk.Frame(box_in)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="添加文件…", command=self._pick_files).pack(side="left")
        ttk.Button(bar, text="添加文件夹…", command=self._pick_folder).pack(side="left", padx=6)
        ttk.Button(bar, text="移除选中", command=self._remove_sel).pack(side="left")
        ttk.Button(bar, text="清空", command=self._clear).pack(side="left", padx=6)

        wrap = ttk.Frame(box_in)
        wrap.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(wrap, height=6, selectmode="extended", activestyle="none")
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=sb.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        box_out = ttk.LabelFrame(outer, text=" 2. 输出与选项 ", padding=8)
        box_out.pack(fill="x", pady=8)
        row = ttk.Frame(box_out)
        row.pack(fill="x")
        self.same_dir = BooleanVar(value=True)
        ttk.Checkbutton(row, text="输出到源文件所在目录", variable=self.same_dir,
                        command=self._toggle_out).pack(side="left")
        self.out_var = StringVar()
        self.out_entry = ttk.Entry(row, textvariable=self.out_var, state="disabled")
        self.out_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.out_btn = ttk.Button(row, text="浏览…", command=self._pick_out, state="disabled")
        self.out_btn.pack(side="left")

        ops = ttk.Frame(box_out)
        ops.pack(fill="x", pady=(8, 0))
        self.opt_notes = BooleanVar(value=True)
        self.opt_hidden = BooleanVar(value=False)
        self.opt_overwrite = BooleanVar(value=True)
        ttk.Checkbutton(ops, text="包含 PPT 备注", variable=self.opt_notes).pack(side="left")
        ttk.Checkbutton(ops, text="包含隐藏工作表", variable=self.opt_hidden).pack(side="left", padx=12)
        ttk.Checkbutton(ops, text="覆盖已存在的 md", variable=self.opt_overwrite).pack(side="left")

        run = ttk.Frame(outer)
        run.pack(fill="x")
        self.start_btn = ttk.Button(run, text="开始转换", command=self._start)
        self.start_btn.pack(side="left")
        ttk.Button(run, text="打开输出目录", command=self._open_out).pack(side="left", padx=6)
        self.progress = ttk.Progressbar(run, mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=8)
        self.status = StringVar(value="就绪")
        ttk.Label(run, textvariable=self.status, width=24).pack(side="left")

        box_log = ttk.LabelFrame(outer, text=" 3. 运行日志 ", padding=6)
        box_log.pack(fill="both", expand=True, pady=(8, 0))
        self.log = tk.Text(box_log, height=9, wrap="word", state="disabled")
        lsb = ttk.Scrollbar(box_log, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=lsb.set)
        self.log.pack(side="left", fill="both", expand=True)
        lsb.pack(side="right", fill="y")

    # ---------------- 交互 ----------------
    def _toggle_out(self) -> None:
        state = "disabled" if self.same_dir.get() else "normal"
        self.out_entry.configure(state=state)
        self.out_btn.configure(state=state)

    def _pick_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择 Office 文件",
            filetypes=[("Office 文档", FILE_PATTERNS), ("所有文件", "*.*")],
        )
        self._add([Path(p) for p in paths])

    def _pick_folder(self) -> None:
        d = filedialog.askdirectory(title="选择文件夹（含子目录）")
        if d:
            self._add([Path(d)])

    def _add(self, paths: list[Path]) -> None:
        added = 0
        for p in paths:
            if p.is_dir():
                found = collect_inputs([p], recursive=True)
                if not found:
                    self._log(f"该目录没有可转换文件：{p}")
                for f in found:
                    if f not in self.files:
                        self.files.append(f)
                        self.listbox.insert("end", str(f))
                        added += 1
            elif p.is_file():
                if p.suffix.lower() not in SUPPORTED_EXTS:
                    self._log(f"跳过不支持的文件：{p.name}")
                    continue
                if p not in self.files:
                    self.files.append(p)
                    self.listbox.insert("end", str(p))
                    added += 1
        if added:
            self._log(f"新增 {added} 个，共 {len(self.files)} 个待转换")
        self.status.set(f"待转换 {len(self.files)} 个")

    def _remove_sel(self) -> None:
        for idx in reversed(self.listbox.curselection()):
            self.listbox.delete(idx)
            del self.files[idx]
        self.status.set(f"待转换 {len(self.files)} 个")

    def _clear(self) -> None:
        self.listbox.delete(0, "end")
        self.files.clear()
        self.status.set("就绪")

    def _pick_out(self) -> None:
        d = filedialog.askdirectory(title="选择输出目录")
        if d:
            self.out_var.set(d)

    def _open_out(self) -> None:
        target = self.out_var.get().strip() if not self.same_dir.get() else ""
        if not target:
            target = str(self.files[0].parent) if self.files else os.getcwd()
        try:
            os.startfile(target)  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showwarning("打开失败", str(exc))

    # ---------------- 转换 ----------------
    def _start(self) -> None:
        if self.running:
            return
        if not self.files:
            messagebox.showinfo("提示", "请先添加要转换的文件或文件夹。")
            return
        out_dir = None
        if not self.same_dir.get():
            out_dir = self.out_var.get().strip()
            if not out_dir:
                messagebox.showinfo("提示", "请选择输出目录，或勾选“输出到源文件所在目录”。")
                return
            try:
                Path(out_dir).mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                messagebox.showerror("输出目录不可用", str(exc))
                return

        options = {
            "include_notes": self.opt_notes.get(),
            "include_hidden_sheets": self.opt_hidden.get(),
            "overwrite": self.opt_overwrite.get(),
        }
        self.running = True
        self.cancel_flag.clear()
        self.start_btn.configure(state="disabled", text="转换中…")
        self.progress.configure(maximum=len(self.files), value=0)
        self.status.set("转换中…")
        self._log("-" * 60)
        threading.Thread(
            target=self._worker, args=(list(self.files), out_dir, options), daemon=True
        ).start()

    def _worker(self, files: list[Path], out_dir, options: dict) -> None:
        results = []
        for i, f in enumerate(files, start=1):
            if self.cancel_flag.is_set():
                break
            self.queue.put(("progress", i, len(files), f))
            res = convert_one(f, out_dir, options)
            results.append(res)
            self.queue.put(("result", res))
        self.queue.put(("done", results))

    def _poll(self) -> None:
        try:
            while True:
                msg = self.queue.get_nowait()
                kind = msg[0]
                if kind == "progress":
                    _, i, total, f = msg
                    self.progress.configure(value=i - 1)
                    self.status.set(f"{i}/{total} 处理中")
                    self._log(f"[{i}/{total}] {f}")
                elif kind == "result":
                    res = msg[1]
                    if res.ok:
                        self._log(f"    成功 → {res.out}  ({res.elapsed:.1f}s)")
                    else:
                        self._log(f"    失败：{res.error}")
                    for w in res.warnings[:5]:
                        self._log(f"    提示：{w}")
                elif kind == "done":
                    results = msg[1]
                    self.progress.configure(value=self.progress["maximum"])
                    ok = sum(1 for r in results if r.ok)
                    fail = len(results) - ok
                    self.status.set(f"完成：成功 {ok}，失败 {fail}")
                    self._log(format_report(results))
                    self._log("转换结束。")
                    self.running = False
                    self.start_btn.configure(state="normal", text="开始转换")
                    if fail:
                        messagebox.showwarning(
                            "部分文件转换失败", f"成功 {ok} 个，失败 {fail} 个。\n详见运行日志。"
                        )
        except queue.Empty:
            pass
        self.root.after(120, self._poll)

    def _log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", str(text).rstrip() + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        log_line(text)


def run() -> int:
    _dpi_aware()
    root = Tk()
    App(root)
    root.mainloop()
    return 0
