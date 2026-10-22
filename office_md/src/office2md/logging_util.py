# -*- coding: utf-8 -*-
"""日志与安全输出。

打包成窗口程序（PyInstaller --windowed）后 sys.stdout 可能为 None，
直接 print 会抛 AttributeError，因此所有控制台输出都经过 safe_print。
"""

from __future__ import annotations

import datetime as _dt
import sys
from pathlib import Path
from typing import Optional

from .core import app_root

_MAX_LOG_BYTES = 4 * 1024 * 1024


def log_dir() -> Path:
    d = app_root() / "logs"
    try:
        d.mkdir(parents=True, exist_ok=True)
        return d
    except Exception:
        return Path(".")


def log_file() -> Path:
    name = "office2md_" + _dt.date.today().strftime("%Y%m%d") + ".log"
    return log_dir() / name


def log_line(text: str) -> None:
    """写运行日志（失败静默，绝不影响主流程）。"""
    try:
        path = log_file()
        if path.exists() and path.stat().st_size > _MAX_LOG_BYTES:
            path.unlink()
        stamp = _dt.datetime.now().strftime("%H:%M:%S")
        with open(path, "a", encoding="utf-8") as fh:
            for line in str(text).rstrip().split("\n"):
                fh.write(f"[{stamp}] {line}\n")
    except Exception:
        pass


def safe_print(text: str = "") -> None:
    try:
        if sys.stdout is not None:
            print(text)
    except Exception:
        pass
    log_line(text)


def has_console() -> bool:
    return getattr(sys, "stdout", None) is not None
