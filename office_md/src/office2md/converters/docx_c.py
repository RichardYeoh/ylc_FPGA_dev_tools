# -*- coding: utf-8 -*-
"""Word（.docx/.docm）转 Markdown。

策略：
1. 主路径 —— 直接用 python-docx 遍历 OOXML，按文档流顺序还原标题、正文、
   列表、表格、图片、超链接；
2. 兜底路径 —— 主路径异常时退回 mammoth（HTML）→ markdownify（md）。

之所以不用 mammoth 当主路径：中文版 Word 的内置样式名存在 "Heading 1" /
"标题 1" 两种写法，自研路径可以直接读 w:outlineLvl 与 styleId，判定更可靠。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Iterator, List

from docx import Document
from docx.document import Document as DocxDocument
from docx.oxml.ns import qn
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph

from ..mdutil import ImageStore, render_table, squash_blank_lines, to_text

_HEADING_RE = re.compile(r"^\s*(?:heading|标题|標題|title)\s*([1-9])\s*$", re.I)
_BULLET_HINT = ("list bullet", "list paragraph", "项目符号", "列表段落")
_NUMBER_HINT = ("list number", "编号列表", "列表编号")

_IGNORED_STYLES = ("toc", "table of figures", "caption", "题注")

# python-docx 的 nsmap 不含 vml(v) 前缀，这里直接写全名，避免 qn() 抛 KeyError
_DRAWING_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_VML_NS = "urn:schemas-microsoft-com:vml"

A_BLIP = f"{{{_DRAWING_NS}}}blip"
R_EMBED = f"{{{_REL_NS}}}embed"
R_LINK = f"{{{_REL_NS}}}link"
R_ID = f"{{{_REL_NS}}}id"
M_OMATH = f"{{{_MATH_NS}}}oMath"
M_T = f"{{{_MATH_NS}}}t"
VML_IMAGEDATA = f"{{{_VML_NS}}}imagedata"


_LIST_LINE_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _list_kind(text: str) -> str:
    """返回列表类型："-" 无序、"1" 有序、"" 非列表。"""
    m = _LIST_LINE_RE.match(text.split("\n", 1)[0])
    if not m:
        return ""
    token = m.group(0).strip()
    return "1" if token[:1].isdigit() else "-"


def _has_h1(body: str) -> bool:
    return any(line.startswith("# ") for line in body.split("\n"))


class DocxConverter:
    """把一个 .docx 文档渲染为 Markdown 文本。"""

    def __init__(self, src: Path, md_path: Path, options: dict | None = None):
        self.src = Path(src)
        self.md_path = Path(md_path)
        self.opt = options or {}
        self.doc: DocxDocument = Document(str(self.src))
        self.images = ImageStore(self.md_path)
        self.warnings: List[str] = []
        self._num_seq: dict[int, int] = {}

    # ------------------------------------------------------------------ #
    # 入口
    # ------------------------------------------------------------------ #
    def convert(self) -> str:
        blocks: List[str] = []
        prev_kind = ""
        for block in self._iter_blocks(self.doc.element.body):
            text = self._render_block(block)
            if not text or not text.strip():
                continue
            text = text.rstrip()
            kind = _list_kind(text)
            if blocks and kind and kind == prev_kind:
                # 同类型相邻列表项只保留单个换行，否则 md 会把它们拆成两个列表
                blocks[-1] = blocks[-1] + "\n" + text
            else:
                blocks.append(text)
            prev_kind = kind

        body = "\n\n".join(blocks)
        title = "" if _has_h1(body) else self._document_title()
        header = f"# {title}\n\n" if title else ""
        return squash_blank_lines(header + body).strip() + "\n"

    # ------------------------------------------------------------------ #
    # 文档流遍历
    # ------------------------------------------------------------------ #
    def _iter_blocks(self, parent) -> Iterator[object]:
        """按 XML 顺序产出 Paragraph / Table，展开内容控件（w:sdt）。"""
        for child in parent.iterchildren():
            tag = child.tag
            if tag == qn("w:p"):
                yield Paragraph(child, self.doc)
            elif tag == qn("w:tbl"):
                yield Table(child, self.doc)
            elif tag == qn("w:sdt"):
                content = child.find(qn("w:sdtContent"))
                if content is not None:
                    yield from self._iter_blocks(content)

    def _render_block(self, block) -> str:
        if isinstance(block, Paragraph):
            return self._render_paragraph(block)
        if isinstance(block, Table):
            return self._render_table(block)
        return ""

    # ------------------------------------------------------------------ #
    # 段落
    # ------------------------------------------------------------------ #
    def _document_title(self) -> str:
        """没有正文一级标题时，用文档属性里的标题补一个。"""
        try:
            props = self.doc.core_properties
            t = (props.title or "").strip()
            return t
        except Exception:
            return ""

    def _heading_level(self, p: Paragraph) -> int:
        # 1) 大纲级别最可靠
        pPr = p._p.pPr
        if pPr is not None:
            lvl = pPr.find(qn("w:outlineLvl"))
            if lvl is not None:
                try:
                    v = int(lvl.get(qn("w:val")))
                    if 0 <= v <= 8:
                        return v + 1
                except (TypeError, ValueError):
                    pass
        # 2) 样式名 / 样式 ID
        style = p.style
        seen = set()
        while style is not None and id(style) not in seen:
            seen.add(id(style))
            name = (getattr(style, "name", "") or "").strip()
            sid = (getattr(style, "style_id", "") or "").strip()
            for candidate in (name, sid):
                m = _HEADING_RE.match(candidate)
                if m:
                    return int(m.group(1))
                m2 = re.match(r"^heading([1-9])$", candidate, re.I)
                if m2:
                    return int(m2.group(1))
            style = getattr(style, "base_style", None)
        return 0

    def _list_marker(self, p: Paragraph) -> tuple[str, int]:
        """返回 (标记, 层级)。标记为空表示不是列表。"""
        name = (p.style.name or "").lower() if p.style is not None else ""
        sid = (p.style.style_id or "").lower() if p.style is not None else ""
        probe = name + " " + sid

        numPr = p._p.pPr.numPr if p._p.pPr is not None else None
        level = 0
        if numPr is not None:
            ilvl = numPr.find(qn("w:ilvl"))
            if ilvl is not None:
                try:
                    level = int(ilvl.get(qn("w:val")))
                except (TypeError, ValueError):
                    level = 0

        is_bullet = any(k in probe for k in _BULLET_HINT)
        is_number = any(k in probe for k in _NUMBER_HINT)
        if not (is_bullet or is_number) and numPr is not None:
            is_bullet = True  # 有编号定义但样式名未知，按无序处理

        if is_number and not is_bullet:
            return "1.", level
        if is_bullet:
            return "-", level
        return "", level

    def _render_paragraph(self, p: Paragraph) -> str:
        text = self._render_inline(p).strip()
        if not text:
            return ""

        level = self._heading_level(p)
        if level:
            self._num_seq.clear()
            return f"{'#' * min(level, 6)} {text}"

        marker, indent = self._list_marker(p)
        if marker:
            pad = "  " * max(0, indent)
            if marker == "1.":
                # 有序列表按层维护自增序号，比统一输出 1. 更易读
                self._num_seq[indent] = self._num_seq.get(indent, 0) + 1
                return f"{pad}{self._num_seq[indent]}. {text}"
            return f"{pad}- {text}"
        self._num_seq.clear()

        style_name = (p.style.name or "").lower() if p.style is not None else ""
        if any(s in style_name for s in ("quote", "引用", "intense quote")):
            return "\n".join(f"> {line}" for line in text.split("\n"))

        return text

    # ------------------------------------------------------------------ #
    # 行内内容（run / 超链接 / 图片 / 公式）
    # ------------------------------------------------------------------ #
    def _render_inline(self, p: Paragraph) -> str:
        parts: List[str] = []
        for child in p._p.iterchildren():
            tag = child.tag
            if tag == qn("w:r"):
                parts.append(self._render_run(child))
            elif tag == qn("w:hyperlink"):
                parts.append(self._render_hyperlink(child))
            elif tag == M_OMATH:
                parts.append(self._render_omml(child))
            elif tag == qn("w:ins"):  # 修订插入
                for sub in child.iterchildren(qn("w:r")):
                    parts.append(self._render_run(sub))
        return "".join(parts)

    def _render_run(self, r_elm) -> str:
        run = _RunWrapper(r_elm, self.doc)
        text = run.text
        images = self._run_images(r_elm)
        if not text and not images:
            return ""
        if text:
            text = self._decorate(text, r_elm)
        return text + "".join(images)

    def _decorate(self, text: str, r_elm) -> str:
        if not text.strip():
            return text
        leading = text[: len(text) - len(text.lstrip())]
        trailing = text[len(text.rstrip()) :]
        core = text.strip()

        rPr = r_elm.find(qn("w:rPr"))
        bold = italic = strike = code = False
        if rPr is not None:
            bold = rPr.find(qn("w:b")) is not None
            italic = rPr.find(qn("w:i")) is not None
            strike = rPr.find(qn("w:strike")) is not None or rPr.find(qn("w:dstrike")) is not None
            fonts = rPr.find(qn("w:rFonts"))
            if fonts is not None:
                name = (fonts.get(qn("w:ascii")) or "") + (fonts.get(qn("w:hAnsi")) or "")
                if any(k in name.lower() for k in ("consolas", "courier", "mono")):
                    code = True

        if code and "`" not in core:
            core = f"`{core}`"
        else:
            if bold and italic:
                core = f"***{core}***"
            elif bold:
                core = f"**{core}**"
            elif italic:
                core = f"*{core}*"
            if strike:
                core = f"~~{core}~~"
        return leading + core + trailing

    def _run_images(self, r_elm) -> List[str]:
        out: List[str] = []
        # DrawingML
        for blip in r_elm.findall(".//" + A_BLIP):
            rid = blip.get(R_EMBED) or blip.get(R_LINK)
            if not rid:
                continue
            blob, ext = self._part_blob(rid)
            if blob:
                md = self.images.markdown(blob, ext, alt="")
                if md:
                    out.append(md)
        # VML（旧版粘贴图片）
        for img in r_elm.findall(".//" + VML_IMAGEDATA):
            rid = img.get(R_ID)
            if not rid:
                continue
            blob, ext = self._part_blob(rid)
            if blob:
                md = self.images.markdown(blob, ext, alt="")
                if md:
                    out.append(md)
        return out

    def _part_blob(self, rid: str) -> tuple[bytes, str]:
        try:
            part = self.doc.part.related_parts[rid]
        except Exception:
            return b"", ""
        blob = getattr(part, "blob", b"") or b""
        ext = Path(str(part.partname)).suffix or ".png"
        return blob, ext

    def _render_hyperlink(self, h_elm) -> str:
        rid = h_elm.get(qn("r:id"))
        url = ""
        if rid:
            try:
                url = self.doc.part.rels[rid].target_ref or ""
            except Exception:
                url = ""
        text = "".join(self._render_run(r) for r in h_elm.iterchildren(qn("w:r"))).strip()
        if not text:
            return ""
        if not url:
            return text
        return f"[{text}]({url})"

    def _render_omml(self, m_elm) -> str:
        """公式：提取纯文本（不做 LaTeX 转换，避免生成错误公式）。"""
        texts = [t.text or "" for t in m_elm.iter(M_T)]
        raw = "".join(texts).strip()
        if not raw:
            return ""
        self.warnings.append("文档包含公式，已按纯文本输出（未做 LaTeX 转换）")
        return f"`{raw}`"

    # ------------------------------------------------------------------ #
    # 表格
    # ------------------------------------------------------------------ #
    def _render_table(self, table: Table) -> str:
        rows: List[List[str]] = []
        # 用元素本身做集合键：lxml 代理对象若被回收，id() 会被复用导致误判合并
        visited: set = set()
        for row in table.rows:
            cells: List[str] = []
            for cell in row.cells:
                tc = cell._tc
                if tc in visited:
                    cells.append("")
                    continue
                visited.add(tc)
                cells.append(self._cell_text(cell))
            rows.append(cells)

        if not rows:
            return ""
        if len(rows[0]) > 12:
            self.warnings.append(f"存在 {len(rows[0])} 列的宽表格，md 中可能显示拥挤")

        rendered = render_table(rows, has_header=True)
        nested = self._nested_tables(table)
        if nested:
            rendered += "\n\n" + "\n\n".join(nested)
        return rendered

    def _nested_tables(self, table: Table) -> List[str]:
        out: List[str] = []
        for row in table.rows:
            for cell in row.cells:
                for sub in cell.tables:
                    out.append(self._render_table(sub))
        return out

    def _cell_text(self, cell: _Cell) -> str:
        parts: List[str] = []
        for child in cell._tc.iterchildren():
            if child.tag == qn("w:p"):
                p = Paragraph(child, self.doc)
                text = self._render_inline(p).strip()
                if text:
                    parts.append(text)
            elif child.tag == qn("w:tbl"):
                self.warnings.append("表格内嵌套表格已展开到表格之后")
        return " <br> ".join(parts)


class _RunWrapper:
    """轻量包装 w:r 元素，复用 python-docx 的 Run.text 语义。"""

    def __init__(self, r_elm, doc):
        self._r = r_elm
        self._doc = doc

    @property
    def text(self) -> str:
        from docx.text.run import Run

        try:
            return Run(self._r, self._doc).text or ""
        except Exception:
            return "".join(t.text or "" for t in self._r.iter(qn("w:t")))


def convert_docx(src: Path, md_path: Path, options: dict | None = None) -> tuple[str, List[str]]:
    conv = DocxConverter(src, md_path, options)
    md = conv.convert()
    return md, conv.warnings


def convert_docx_fallback(src: Path, md_path: Path, options: dict | None = None) -> tuple[str, List[str]]:
    """兜底：mammoth → HTML → markdownify。"""
    import mammoth
    from markdownify import markdownify as md_convert  # noqa: N813

    store = ImageStore(md_path)
    warnings: List[str] = []

    def _image(image):
        with image.open() as f:
            data = f.read()
        ext = "." + (image.content_type or "image/png").split("/")[-1]
        rel = store.save(data, ext)
        return {"src": rel} if rel else {}

    with open(src, "rb") as fh:
        result = mammoth.convert_to_html(fh, convert_image=mammoth.images.img_element(_image))
    for msg in result.messages:
        warnings.append(str(msg))
    html = result.value or ""
    md = md_convert(html, heading_style="ATX", bullets="-")
    return squash_blank_lines(md).strip() + "\n", warnings
