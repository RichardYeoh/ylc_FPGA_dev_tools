# -*- coding: utf-8 -*-
"""生成回归测试用的 Office 样例文件（docx / xlsx / pptx）。

用法： python tools/make_samples.py [输出目录=samples]
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path


def make_png(path: Path, text: str = "IMG") -> Path:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (320, 120), (240, 244, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([2, 2, 317, 117], outline=(60, 110, 180), width=3)
    d.text((20, 50), text, fill=(30, 60, 120))
    img.save(path)
    return path


def make_docx(out: Path, png: Path) -> Path:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    doc.core_properties.title = "FPGA 设计说明（示例）"

    doc.add_heading("1 概述", level=1)
    p = doc.add_paragraph()
    r = p.add_run("本文件用于验证 ")
    r.bold = True
    r2 = p.add_run("Word→Markdown")
    r2.italic = True
    p.add_run(" 转换效果，包含普通段落、格式、列表、表格、图片与超链接。")

    doc.add_heading("1.1 功能列表", level=2)
    for item in ["支持标题层级", "支持粗体与斜体", "支持表格与图片"]:
        doc.add_paragraph(item, style="List Bullet")
    for item in ["第一步：选择文件", "第二步：点击转换"]:
        doc.add_paragraph(item, style="List Number")

    doc.add_heading("1.2 资源统计", level=2)
    table = doc.add_table(rows=3, cols=4)
    table.style = "Table Grid"
    data = [
        ["模块", "LUT", "FF", "说明"],
        ["uart_rx", "128", "96", "串口接收"],
        ["spi_master", "256", "180", "SPI 主机"],
    ]
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            table.cell(i, j).text = val

    doc.add_heading("1.3 结构示意图", level=2)
    doc.add_picture(str(png), width=None)

    doc.add_heading("1.4 参考链接", level=2)
    doc.add_paragraph("详见 官方文档（示例链接）：https://example.com/doc")

    path = out / "示例-设计说明.docx"
    doc.save(path)
    return path


def make_xlsx(out: Path) -> Path:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "资源占用"
    ws.append(["模块", "LUT", "FF", "BRAM", "频率(MHz)"])
    ws.append(["uart_rx", 128, 96, 0, 100.0])
    ws.append(["spi_master", 256, 180, 1, 125.5])
    ws.append(["ddr_ctrl", 1024, 900, 8, 200])
    ws.append([])
    ws["A7"] = "合计"
    ws["B7"] = "=SUM(B2:B4)"
    ws.merge_cells("A9:D9")
    ws["A9"] = "注：以上为综合后估算值"
    ws["A10"] = dt.date(2026, 10, 21)

    ws2 = wb.create_sheet("接口定义")
    ws2.append(["信号", "方向", "位宽", "说明"])
    ws2.append(["clk", "in", 1, "系统时钟"])
    ws2.append(["rst_n", "in", 1, "异步复位，低有效"])
    ws2.append(["data_out", "out", 32, "数据输出"])

    ws3 = wb.create_sheet("隐藏页")
    ws3.append(["这页是隐藏的"])
    ws3.sheet_state = "hidden"

    path = out / "示例-资源统计.xlsx"
    wb.save(path)
    return path


def make_pptx(out: Path, png: Path) -> Path:
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    s1 = prs.slides.add_slide(prs.slide_layouts[0])
    s1.shapes.title.text = "FPGA 项目汇报（示例）"
    s1.placeholders[1].text = "2026-10-21"

    s2 = prs.slides.add_slide(prs.slide_layouts[1])
    s2.shapes.title.text = "本期进展"
    body = s2.placeholders[1].text_frame
    body.text = "完成 DataMover 通路调试"
    for txt in ["时序收敛到 200MHz", "资源占用下降 12%"]:
        p = body.add_paragraph()
        p.text = txt
        p.level = 1

    s3 = prs.slides.add_slide(prs.slide_layouts[5])
    s3.shapes.title.text = "资源对比表"
    rows, cols = 3, 3
    tbl = s3.shapes.add_table(rows, cols, Inches(1), Inches(2), Inches(8), Inches(2)).table
    data = [["模块", "优化前", "优化后"], ["uart_rx", "150", "128"], ["ddr_ctrl", "1200", "1024"]]
    for i in range(rows):
        for j in range(cols):
            tbl.cell(i, j).text = data[i][j]

    s4 = prs.slides.add_slide(prs.slide_layouts[5])
    s4.shapes.title.text = "框图"
    s4.shapes.add_picture(str(png), Inches(1), Inches(2))

    s4.notes_slide.notes_text_frame.text = "备注：这里讲一下数据通路的分段策略。"

    path = out / "示例-项目汇报.pptx"
    prs.save(path)
    return path


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("samples")
    out.mkdir(parents=True, exist_ok=True)
    png = make_png(out / "示例图片.png", "FPGA BLOCK")
    files = [make_docx(out, png), make_xlsx(out), make_pptx(out, png)]
    for f in files:
        print(f"生成 {f}  ({f.stat().st_size} 字节)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
