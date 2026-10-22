# -*- coding: utf-8 -*-
"""转换调度核心：格式判定、批量遍历、结果汇总、错误隔离。"""

from __future__ import annotations

import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence

from . import EXT_MAP
from .converters.docx_c import convert_docx, convert_docx_fallback
from .converters.pptx_c import convert_pptx
from .converters.xlsx_c import convert_xls, convert_xlsx
from .office_com import OfficeConversionError, TempWorkspace, doc_to_docx, ppt_to_pptx, xls_to_xlsx

# 跳过这些目录，避免把临时/版本库内容当输入
SKIP_DIRS = {"_files", "node_modules", ".git", ".svn", "__pycache__", "vendor", ".venv", "venv"}


def app_root() -> Path:
    """程序根目录：打包后是可执行文件所在目录，源码运行时是项目根。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def temp_root() -> Path:
    p = app_root() / "temp"
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        return Path(os.environ.get("TEMP", "."))


@dataclass
class Result:
    src: Path
    out: Optional[Path] = None
    ok: bool = True
    warnings: List[str] = field(default_factory=list)
    error: str = ""
    elapsed: float = 0.0

    @property
    def message(self) -> str:
        if self.ok:
            return f"OK  {self.src.name} -> {self.out.name if self.out else ''}"
        return f"FAIL {self.src.name}: {self.error}"


def is_supported(path: Path) -> bool:
    return Path(path).suffix.lower() in EXT_MAP


def collect_inputs(targets: Sequence[str | Path], recursive: bool = True) -> List[Path]:
    """把用户给出的文件/目录展开成待转换文件列表（去重、保序）。"""
    files: List[Path] = []
    seen = set()
    for t in targets:
        p = Path(t)
        if p.is_file():
            cand = [p]
        elif p.is_dir():
            it = p.rglob("*") if recursive else p.glob("*")
            cand = [f for f in it if f.is_file()]
        else:
            continue
        for f in cand:
            if not is_supported(f):
                continue
            if any(part.lower() in SKIP_DIRS for part in f.parts):
                continue
            rp = f.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            files.append(f)
    return files


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def target_path(src: Path, out_dir: Optional[Path]) -> Path:
    if out_dir is None:
        return src.with_suffix(".md")
    return Path(out_dir) / (src.stem + ".md")


def _dispatch(src: Path, md_path: Path, options: dict, warnings: List[str]) -> str:
    ext = src.suffix.lower()
    kind = EXT_MAP.get(ext)
    if kind is None:
        raise ValueError(f"不支持的文件类型：{ext}")

    # 老格式会先转存到临时文件，标题必须沿用原始文件名
    options = dict(options)
    options.setdefault("title_name", src.stem)

    if kind == "docx":
        try:
            md, w = convert_docx(src, md_path, options)
            warnings.extend(w)
            if md.strip():
                return md
            raise RuntimeError("主解析器输出为空")
        except Exception as exc:
            warnings.append(f"主解析器失败，改用 mammoth 兜底：{exc}")
            md, w = convert_docx_fallback(src, md_path, options)
            warnings.extend(w)
            return md

    if kind == "pptx":
        md, w = convert_pptx(src, md_path, options)
        warnings.extend(w)
        return md

    if kind == "xlsx":
        md, w = convert_xlsx(src, md_path, options)
        warnings.extend(w)
        return md

    if kind == "xls":
        try:
            md, w = convert_xls(src, md_path, options)
            warnings.extend(w)
            if md.strip():
                return md
            raise RuntimeError("xlrd 输出为空")
        except Exception as exc:
            warnings.append(f"xlrd 直接解析失败，改用 Office 转 xlsx：{exc}")
            with TempWorkspace(temp_root()) as tmp:
                xlsx = xls_to_xlsx(src, tmp)
                md, w = convert_xlsx(xlsx, md_path, options)
                warnings.extend(w)
                return md

    if kind in ("doc", "ppt"):
        with TempWorkspace(temp_root()) as tmp:
            if kind == "doc":
                new_src = doc_to_docx(src, tmp)
                md, w = convert_docx(new_src, md_path, options)
            else:
                new_src = ppt_to_pptx(src, tmp)
                md, w = convert_pptx(new_src, md_path, options)
            warnings.extend(w)
            return md

    raise ValueError(f"内部错误：未知类型 {kind}")


def convert_one(
    src: str | Path,
    out_dir: Optional[str | Path] = None,
    options: Optional[dict] = None,
) -> Result:
    """转换单个文件。异常被收敛到 Result，不向上抛。"""
    src = Path(src)
    opt = dict(options or {})
    res = Result(src=src)
    started = time.time()
    md_path = target_path(src, Path(out_dir) if out_dir else None)

    if md_path.exists() and not opt.get("overwrite", True):
        res.ok = False
        res.error = f"目标文件已存在：{md_path.name}（未开启覆盖）"
        res.elapsed = time.time() - started
        return res

    try:
        md = _dispatch(src, md_path, opt, res.warnings)
        if not md or not md.strip():
            raise RuntimeError("转换结果为空（可能文档没有可提取的文字）")
        _write_text(md_path, md)
        res.out = md_path
    except OfficeConversionError as exc:
        res.ok = False
        res.error = str(exc)
    except PermissionError as exc:
        res.ok = False
        res.error = f"文件被占用或无权限：{exc}"
    except Exception as exc:
        res.ok = False
        res.error = f"{type(exc).__name__}: {exc}"
        if opt.get("debug"):
            res.warnings.append(traceback.format_exc())
    res.elapsed = time.time() - started
    return res


ProgressFn = Callable[[int, int, Path], None]


def convert_many(
    targets: Sequence[str | Path],
    out_dir: Optional[str | Path] = None,
    options: Optional[dict] = None,
    recursive: bool = True,
    progress: Optional[ProgressFn] = None,
    cancel_flag: Optional[Callable[[], bool]] = None,
) -> List[Result]:
    """批量转换。目录输入可以保持相对目录结构输出。"""
    files = collect_inputs(targets, recursive=recursive)
    results: List[Result] = []
    total = len(files)
    out_root = Path(out_dir) if out_dir else None

    for i, f in enumerate(files, start=1):
        if cancel_flag and cancel_flag():
            break
        dest_dir = out_root
        if out_root is not None:
            # 目录输入：把源文件相对父目录的路径搬到输出目录下
            for t in targets:
                tp = Path(t)
                if tp.is_dir():
                    try:
                        rel = f.resolve().relative_to(tp.resolve()).parent
                    except ValueError:
                        continue
                    dest_dir = out_root / rel
                    break
        if progress:
            progress(i, total, f)
        results.append(convert_one(f, dest_dir, options))
    return results


def summarize(results: Sequence[Result]) -> dict:
    ok = sum(1 for r in results if r.ok)
    return {
        "total": len(results),
        "ok": ok,
        "fail": len(results) - ok,
        "warnings": sum(len(r.warnings) for r in results),
    }


def format_report(results: Sequence[Result]) -> str:
    s = summarize(results)
    lines = [f"总计 {s['total']} 个文件：成功 {s['ok']}，失败 {s['fail']}，警告 {s['warnings']} 条"]
    for r in results:
        status = "OK  " if r.ok else "FAIL"
        lines.append(f"[{status}] {r.src.name}  ({r.elapsed:.1f}s)")
        if not r.ok:
            lines.append(f"        原因：{r.error}")
        for w in r.warnings[:10]:
            lines.append(f"        提示：{w}")
        if len(r.warnings) > 10:
            lines.append(f"        …… 另有 {len(r.warnings) - 10} 条提示")
    return "\n".join(lines)
