# -*- coding: utf-8 -*-
"""命令行入口：不带参数启动图形界面，带参数执行批量转换。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .core import convert_many, format_report, summarize
from .logging_util import log_line, safe_print


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="office2md",
        description="把 Word / Excel / PowerPoint 转成 Markdown（完全离线）。不带参数时启动图形界面。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "示例：\n"
            "  office2md                          启动图形界面\n"
            "  office2md 报告.docx                转换单个文件，md 输出到源文件同目录\n"
            "  office2md D:\\资料 -o D:\\out        转换整个目录\n"
            "  office2md a.docx b.xlsx -o out --no-notes\n"
        ),
    )
    p.add_argument("targets", nargs="*", help="要转换的文件或目录（可多个）")
    p.add_argument("-o", "--output-dir", default=None, help="输出目录（默认与源文件同目录）")
    p.add_argument("--no-recursive", action="store_true", help="目录输入时不递归子目录")
    p.add_argument("--no-notes", action="store_true", help="不输出 PPT 演讲者备注")
    p.add_argument("--hidden-sheets", action="store_true", help="包含 Excel 隐藏工作表")
    p.add_argument("--no-overwrite", action="store_true", help="已存在的 md 不覆盖")
    p.add_argument("--debug", action="store_true", help="失败时输出完整堆栈到日志")
    p.add_argument("-v", "--version", action="version", version=f"office2md {__version__}")
    return p


def _setup_console() -> None:
    """把 Windows 控制台切到 UTF-8，避免中文输出乱码。"""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is not None:
                stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def main(argv: list[str] | None = None, force_cli: bool = False) -> int:
    _setup_console()
    argv = list(sys.argv[1:] if argv is None else argv)

    # 无参数：窗口版启动图形界面；控制台版直接打印帮助，避免残留黑框
    if not argv:
        if force_cli:
            build_parser().print_help()
            return 0
        try:
            from .gui import run

            return run()
        except Exception as exc:
            safe_print(f"图形界面启动失败：{exc}")
            safe_print("可改用命令行方式：office2md <文件或目录> [-o 输出目录]")
            return 2

    args = build_parser().parse_args(argv)
    if not args.targets:
        build_parser().print_help()
        return 0

    options = {
        "include_notes": not args.no_notes,
        "include_hidden_sheets": args.hidden_sheets,
        "overwrite": not args.no_overwrite,
        "debug": args.debug,
    }

    targets = [Path(t) for t in args.targets]
    missing = [str(t) for t in targets if not t.exists()]
    if missing:
        safe_print("以下路径不存在：" + "；".join(missing))
        return 2

    out_dir = Path(args.output_dir) if args.output_dir else None
    if out_dir is not None:
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            safe_print(f"输出目录不可用：{exc}")
            return 2

    safe_print(f"office2md {__version__}  开始转换……")

    def _progress(i: int, total: int, path: Path) -> None:
        safe_print(f"[{i}/{total}] {path}")

    results = convert_many(
        targets,
        out_dir=out_dir,
        options=options,
        recursive=not args.no_recursive,
        progress=_progress,
    )

    if not results:
        safe_print("没有找到可转换的 Office 文件（支持 .doc/.docx/.xls/.xlsx/.ppt/.pptx）。")
        return 1

    safe_print("")
    safe_print(format_report(results))
    s = summarize(results)
    return 0 if s["fail"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
