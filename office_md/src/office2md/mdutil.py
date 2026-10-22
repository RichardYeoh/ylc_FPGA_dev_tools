# -*- coding: utf-8 -*-
"""Markdown 生成辅助工具：文本转义、表格渲染、图片落盘管理。"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterable, Sequence

_EOL_RE = re.compile(r"\r\n|\r")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")


# --------------------------------------------------------------------------- #
# 基础文本处理
# --------------------------------------------------------------------------- #
def to_text(value) -> str:
    """把任意单元格/段落值转成字符串，数字去掉多余的 .0。"""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if value != value:  # NaN
            return ""
        if value == int(value) and abs(value) < 1e16:
            return str(int(value))
        return repr(value)
    return str(value)


def normalize_newlines(text: str) -> str:
    return _EOL_RE.sub("\n", text)


def squash_blank_lines(text: str) -> str:
    """把 3 个及以上连续空行压成 2 行，避免 md 中出现大片空白。"""
    return _MULTI_BLANK_RE.sub("\n\n", normalize_newlines(text))


def clean_cell(value, newline_as_br: bool = True) -> str:
    """转义 md 表格中会破坏结构的字符，并把换行折叠。"""
    s = normalize_newlines(to_text(value)).strip()
    if not s:
        return ""
    s = s.replace("|", "\\|")
    if newline_as_br:
        s = " <br> ".join(part.strip() for part in s.split("\n") if part.strip())
    else:
        s = " ".join(part.strip() for part in s.split("\n") if part.strip())
    return s


def escape_md(text: str) -> str:
    """转义正文中可能被误解析为 md 语法的字符（保守策略，只处理关键字符）。"""
    if not text:
        return ""
    out = []
    for ch in text:
        if ch in "\\`*{}[]":
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def heading(level: int, text: str) -> str:
    level = max(1, min(6, level))
    return f"{'#' * level} {text.strip()}".rstrip()


def fence_code(text: str, lang: str = "") -> str:
    """用足够长的反引号围栏包裹内容，避免内容自带 ``` 造成断裂。"""
    runs = re.findall(r"`+", text or "")
    fence = "`" * max(3, max((len(r) for r in runs), default=0) + 1)
    return f"{fence}{lang}\n{text or ''}\n{fence}"


# --------------------------------------------------------------------------- #
# 表格渲染
# --------------------------------------------------------------------------- #
def render_table(
    rows: Sequence[Sequence[object]],
    has_header: bool = True,
    max_cols: int | None = None,
    newline_as_br: bool = True,
) -> str:
    """把二维数据渲染为 GitHub 风格 Markdown 表格。

    - 自动补齐列数并丢弃全空列；
    - has_header=True 时第一行作为表头；
    - 全部为空时返回空字符串（调用方据此跳过）。
    """
    if not rows:
        return ""

    width = max(len(r) for r in rows)
    if max_cols is not None:
        width = min(width, max_cols)
    grid = [[clean_cell(c, newline_as_br) for c in (list(r) + [""] * width)[:width]] for r in rows]

    keep = [i for i in range(width) if any(g[i] for g in grid)]
    if not keep:
        return ""
    grid = [[g[i] for i in keep] for g in grid]

    ncol = len(grid[0])
    if has_header:
        header = grid[0]
        body = grid[1:]
    else:
        header = [""] * ncol
        body = grid
    header = [h if h else " " for h in header]

    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * ncol) + " |",
    ]
    for row in body:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 图片落盘
# --------------------------------------------------------------------------- #
class ImageStore:
    """把文档内嵌图片保存为独立文件，并返回 md 中引用的相对路径。

    默认与 md 文件同级建一个 `<md名>_files/` 目录，保持 md 单文件可读、可移动。
    """

    def __init__(self, md_path: Path, folder_suffix: str = "_files", extra_folder: str | None = None):
        self.md_path = Path(md_path)
        self.folder_name = extra_folder or (self.md_path.stem + folder_suffix)
        self.folder = self.md_path.parent / self.folder_name
        self._seen: dict[str, str] = {}
        self.count = 0

    def _ensure(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, ext: str = ".png", alt: str = "") -> str:
        if not data:
            return ""
        ext = (ext or ".png").lower()
        if not ext.startswith("."):
            ext = "." + ext
        digest = hashlib.sha1(data).hexdigest()[:16]
        if digest in self._seen:
            return self._seen[digest]

        self._ensure()
        self.count += 1
        name = f"image{self.count:03d}{ext}"
        target = self.folder / name
        target.write_bytes(data)
        rel = f"{self.folder_name}/{name}"
        self._seen[digest] = rel
        return rel

    def markdown(self, data: bytes, ext: str = ".png", alt: str = "") -> str:
        rel = self.save(data, ext, alt)
        if not rel:
            return ""
        safe_alt = (alt or "").replace("]", "").replace("[", "").replace("\n", " ")
        return f"![{safe_alt}]({rel})"


def ensure_parent(path: Path) -> Path:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return Path(path)
