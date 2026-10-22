# -*- coding: utf-8 -*-
"""老格式 .doc / .ppt / .xls 的兼容层：调用本机已安装的 Microsoft Office。

设计约束：
- 只在本机 Office 存在时才启用（目标内网机已确认装有 Office）；
- 用 DispatchEx 起独立实例，避免干扰用户正在编辑的文档；
- 一律以只读方式打开源文件，另存到临时目录后再交给 OOXML 解析器；
- 任何异常都必须保证应用退出，不残留后台进程。
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

# Office 常量
WD_FORMAT_DOCUMENT_DEFAULT = 16  # .docx
PP_SAVE_AS_OPENXML_PRESENTATION = 24  # .pptx
XL_OPENXML_WORKBOOK = 51  # .xlsx

_PROGIDS = {
    "word": "Word.Application",
    "excel": "Excel.Application",
    "powerpoint": "PowerPoint.Application",
}


def _reg_has(progid: str) -> bool:
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid):
            return True
    except Exception:
        return False


def detect_office() -> dict:
    """返回各 Office 应用是否可用（只看注册表，不启动进程）。"""
    status = {k: _reg_has(v) for k, v in _PROGIDS.items()}
    try:
        import win32com.client  # noqa: F401

        status["pywin32"] = True
    except Exception:
        status["pywin32"] = False
    return status


def _temp_dir() -> Path:
    d = Path(tempfile.mkdtemp(prefix="office2md_"))
    return d


class OfficeConversionError(RuntimeError):
    pass


def _require(app_key: str) -> None:
    if not _reg_has(_PROGIDS[app_key]):
        raise OfficeConversionError(
            f"本机未检测到 Microsoft {app_key.capitalize()}，无法转换老格式文件。"
            " 请安装 Office，或用 Office 手动另存为 .docx/.pptx 后再转换。"
        )
    try:
        import win32com.client  # noqa: F401
    except Exception as exc:
        raise OfficeConversionError(f"缺少 pywin32 组件，无法调用 Office：{exc}") from exc


def doc_to_docx(src: Path, work_dir: Path) -> Path:
    """Word .doc → .docx。"""
    _require("word")
    import pythoncom
    import win32com.client as win32

    src = Path(src).resolve()
    dst = Path(work_dir) / (src.stem + "_conv.docx")
    pythoncom.CoInitialize()
    app = None
    doc = None
    try:
        app = win32.DispatchEx("Word.Application")
        app.Visible = False
        app.DisplayAlerts = 0
        doc = app.Documents.Open(str(src), ReadOnly=True, AddToRecentFiles=False, Visible=False)
        doc.SaveAs2(str(dst), FileFormat=WD_FORMAT_DOCUMENT_DEFAULT)
    finally:
        try:
            if doc is not None:
                doc.Close(SaveChanges=0)
        except Exception:
            pass
        try:
            if app is not None:
                app.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
    if not dst.exists():
        raise OfficeConversionError("Word 另存 .docx 失败（未生成目标文件）")
    return dst


def ppt_to_pptx(src: Path, work_dir: Path) -> Path:
    """PowerPoint .ppt → .pptx。"""
    _require("powerpoint")
    import pythoncom
    import win32com.client as win32

    src = Path(src).resolve()
    dst = Path(work_dir) / (src.stem + "_conv.pptx")
    pythoncom.CoInitialize()
    app = None
    pres = None
    try:
        app = win32.DispatchEx("PowerPoint.Application")
        pres = app.Presentations.Open(str(src), ReadOnly=True, WithWindow=False)
        pres.SaveAs(str(dst), PP_SAVE_AS_OPENXML_PRESENTATION)
    finally:
        try:
            if pres is not None:
                pres.Close()
        except Exception:
            pass
        try:
            if app is not None:
                app.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
    if not dst.exists():
        raise OfficeConversionError("PowerPoint 另存 .pptx 失败（未生成目标文件）")
    return dst


def xls_to_xlsx(src: Path, work_dir: Path) -> Path:
    """Excel .xls → .xlsx（仅在 xlrd 无法读取时的兜底）。"""
    _require("excel")
    import pythoncom
    import win32com.client as win32

    src = Path(src).resolve()
    dst = Path(work_dir) / (src.stem + "_conv.xlsx")
    pythoncom.CoInitialize()
    app = None
    wb = None
    try:
        app = win32.DispatchEx("Excel.Application")
        app.Visible = False
        app.DisplayAlerts = False
        wb = app.Workbooks.Open(str(src), ReadOnly=True, UpdateLinks=0)
        wb.SaveAs(str(dst), FileFormat=XL_OPENXML_WORKBOOK)
    finally:
        try:
            if wb is not None:
                wb.Close(SaveChanges=False)
        except Exception:
            pass
        try:
            if app is not None:
                app.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
    if not dst.exists():
        raise OfficeConversionError("Excel 另存 .xlsx 失败（未生成目标文件）")
    return dst


class TempWorkspace:
    """转换期的临时目录，退出时自动清理（R7）。"""

    def __init__(self, base: Optional[Path] = None):
        if base is not None:
            Path(base).mkdir(parents=True, exist_ok=True)
            self.path = Path(tempfile.mkdtemp(prefix="conv_", dir=str(base)))
        else:
            self.path = Path(tempfile.mkdtemp(prefix="office2md_"))

    def __enter__(self) -> Path:
        return self.path

    def __exit__(self, *exc) -> None:
        try:
            shutil.rmtree(self.path, ignore_errors=True)
        except Exception:
            pass
