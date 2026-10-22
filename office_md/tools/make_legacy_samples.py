# -*- coding: utf-8 -*-
"""用本机 Office 把 samples 里的新格式文件另存为老格式（.doc/.xls/.ppt），
用于验证老格式兼容路径。

用法： python tools/make_legacy_samples.py
"""

from __future__ import annotations

import sys
from pathlib import Path

WD_FORMAT_DOCUMENT = 0
XL_EXCEL8 = -4143
PP_SAVE_AS_PRESENTATION = 1


def main() -> int:
    base = Path("samples")
    out = Path("samples_legacy")
    out.mkdir(parents=True, exist_ok=True)

    import pythoncom
    import win32com.client as win32

    pythoncom.CoInitialize()
    made = []

    # docx -> doc
    app = None
    try:
        app = win32.DispatchEx("Word.Application")
        app.Visible = False
        app.DisplayAlerts = 0
        src = (base / "示例-设计说明.docx").resolve()
        dst = (out / "示例-设计说明.doc").resolve()
        doc = app.Documents.Open(str(src), ReadOnly=True, AddToRecentFiles=False, Visible=False)
        doc.SaveAs2(str(dst), FileFormat=WD_FORMAT_DOCUMENT)
        doc.Close(0)
        made.append(dst)
    finally:
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass

    # xlsx -> xls
    app = None
    try:
        app = win32.DispatchEx("Excel.Application")
        app.Visible = False
        app.DisplayAlerts = False
        src = (base / "示例-资源统计.xlsx").resolve()
        dst = (out / "示例-资源统计.xls").resolve()
        wb = app.Workbooks.Open(str(src), ReadOnly=True, UpdateLinks=0)
        wb.SaveAs(str(dst), FileFormat=XL_EXCEL8)
        wb.Close(SaveChanges=False)
        made.append(dst)
    finally:
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass

    # pptx -> ppt
    app = None
    try:
        app = win32.DispatchEx("PowerPoint.Application")
        src = (base / "示例-项目汇报.pptx").resolve()
        dst = (out / "示例-项目汇报.ppt").resolve()
        pres = app.Presentations.Open(str(src), ReadOnly=True, WithWindow=False)
        pres.SaveAs(str(dst), PP_SAVE_AS_PRESENTATION)
        pres.Close()
        made.append(dst)
    finally:
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass

    pythoncom.CoUninitialize()
    for p in made:
        print(f"生成 {p}  ({p.stat().st_size} 字节)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
