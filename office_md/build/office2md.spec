# -*- mode: python ; coding: utf-8 -*-
r"""PyInstaller 打包配置（onedir / 无控制台窗口）。

用法（项目根目录下执行）：
    pyinstaller --noconfirm --clean --distpath dist --workpath build\work build\office2md.spec
产物：dist\office2md\office2md.exe + dist\office2md\_internal\
"""

import sys
from pathlib import Path

PROJ = Path(SPECPATH).resolve().parent  # spec 位于 <项目根>/build/，其父目录即项目根

a = Analysis(
    [str(PROJ / "app.py")],
    pathex=[str(PROJ / "src")],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Office COM（老格式兜底）
        "win32com",
        "win32com.client",
        "win32com.client.dynamic",
        "pythoncom",
        "pywintypes",
        "win32timezone",
        # 解析库中按需导入的部分
        "lxml._elementpath",
        "lxml.etree",
        "PIL._tkinter_finder",
        "PIL.Image",
        "PIL.ImageDraw",
        "openpyxl.cell._writer",
        "mammoth",
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "pandas",
        "numpy",
        "matplotlib",
        "scipy",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "IPython",
        "pytest",
        "notebook",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe_gui = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="office2md",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

exe_cli = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="office2md-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe_gui,
    exe_cli,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="office2md",
)
