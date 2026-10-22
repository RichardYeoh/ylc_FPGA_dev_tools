# -*- coding: utf-8 -*-
"""统一入口（源码运行 + PyInstaller 打包共用）。

用法：
    python app.py                # 图形界面
    python app.py 文件或目录 ...  # 命令行批量转换
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SRC = _HERE / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


def _redirect_none_streams() -> None:
    """窗口模式下 sys.stdout/stderr 可能是 None，统一指向空设备避免崩溃。"""
    for name in ("stdout", "stderr"):
        if getattr(sys, name, None) is None:
            try:
                setattr(sys, name, open(os.devnull, "w", encoding="utf-8"))
            except Exception:
                pass


def _is_cli_build() -> bool:
    """打包出两个入口：office2md.exe（窗口）与 office2md-cli.exe（控制台）。"""
    if not getattr(sys, "frozen", False):
        return False
    return Path(sys.executable).stem.lower().endswith("-cli")


def main() -> int:
    _redirect_none_streams()
    from office2md.cli import main as cli_main

    return cli_main(force_cli=_is_cli_build())


if __name__ == "__main__":
    sys.exit(main())
