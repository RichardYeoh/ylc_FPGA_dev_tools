# -*- coding: utf-8 -*-
"""重建 runtime/（源码便携版使用的嵌入式 Python 运行时）。

runtime/ 属于可再生产物，不入 git。任何人在开发机上执行本脚本即可还原：

    python tools/build_runtime.py

前提：
  - 开发机装有 Python 3.13 x64（与发布版本一致），且已加入 PATH；
  - vendor/runtime/python-3.13.0-embed-amd64.zip 存在（随项目入库）；
  - vendor/wheels/ 下有所需 wheel（随项目入库）。

产出 runtime/ 的构成：
  - Python 3.13 embeddable 解压内容
  - tcl/ 与 Lib/tkinter/、_tkinter.pyd（embeddable 包本身不含 tkinter）
  - Lib/site-packages/（离线安装 requirements.txt）
  - python313._pth（把 Lib、Lib\\site-packages、..\\src 加入搜索路径）
  - pywin32 的 DLL 复制到 runtime 根目录（否则 import win32com 会失败）
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ROOT / "runtime"
EMBED_ZIP = ROOT / "vendor" / "runtime" / "python-3.13.0-embed-amd64.zip"
WHEELS = ROOT / "vendor" / "wheels"

PTH_CONTENT = """python313.zip
.
Lib
Lib\\site-packages
..\\src
import site
"""


def step(msg: str) -> None:
    print(f"[{msg}]")


def check_prereq() -> None:
    if not EMBED_ZIP.exists():
        raise SystemExit(f"缺少嵌入式运行时压缩包：{EMBED_ZIP}")
    if sys.version_info[:2] != (3, 13):
        print(f"[警告] 当前 Python 为 {sys.version.split()[0]}，建议使用 3.13 以避免 ABI 不一致")
    if not WHEELS.exists():
        raise SystemExit(f"缺少离线 wheel 目录：{WHEELS}")


def unpack_embed() -> None:
    step("1/5 解压嵌入式运行时")
    RUNTIME.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(EMBED_ZIP) as zf:
        zf.extractall(RUNTIME)


def copy_tkinter() -> None:
    step("2/5 补齐 tkinter 与 Tcl/Tk")
    base = Path(sysconfig.get_paths()["data"])
    tcl_src = base / "tcl"
    tk_pkg = base / "Lib" / "tkinter"
    tk_pyd = base / "DLLs" / "_tkinter.pyd"
    if not tk_pyd.exists():
        tk_pyd = base / "_tkinter.pyd"

    if not tcl_src.exists() or not tk_pkg.exists():
        print("    [警告] 本机未找到 tcl/ 或 Lib/tkinter/，图形界面将不可用")
        return

    shutil.copytree(tcl_src, RUNTIME / "tcl", dirs_exist_ok=True)
    shutil.copytree(tk_pkg, RUNTIME / "Lib" / "tkinter", dirs_exist_ok=True)
    if tk_pyd.exists():
        shutil.copy2(tk_pyd, RUNTIME / tk_pyd.name)
    else:
        print("    [警告] 未找到 _tkinter.pyd")


def write_pth() -> None:
    step("3/5 写入 python313._pth")
    (RUNTIME / "python313._pth").write_text(PTH_CONTENT, encoding="utf-8")


def install_deps() -> None:
    step("4/5 离线安装依赖到 runtime\\Lib\\site-packages")
    target = RUNTIME / "Lib" / "site-packages"
    target.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--target",
        str(target),
        "--no-index",
        f"--find-links={WHEELS}",
        "-r",
        str(ROOT / "requirements.txt"),
        "--no-warn-script-location",
        "--disable-pip-version-check",
    ]
    subprocess.run(cmd, check=True)


def fix_pywin32() -> None:
    step("5/5 复制 pywin32 的 DLL 到 runtime 根目录")
    src = RUNTIME / "Lib" / "site-packages" / "pywin32_system32"
    if not src.exists():
        print("    [提示] 未找到 pywin32_system32，老格式 Office 转换可能不可用")
        return
    for dll in src.glob("*.dll"):
        shutil.copy2(dll, RUNTIME / dll.name)


def verify() -> int:
    python = RUNTIME / "python.exe"
    if not python.exists():
        print("[错误] runtime\\python.exe 不存在")
        return 1
    print("[校验] 尝试导入全部依赖……")
    code = (
        "import docx, openpyxl, pptx, xlrd, mammoth, markdownify, win32com.client, tkinter;"
        "print('ALL_IMPORT_OK')"
    )
    return subprocess.run([str(python), "-c", code]).returncode


def main() -> int:
    print("=" * 50)
    print(" 重建 runtime\\ （源码便携版运行时）")
    print("=" * 50)
    check_prereq()
    unpack_embed()
    copy_tkinter()
    write_pth()
    install_deps()
    fix_pywin32()
    rc = verify()
    print("")
    if rc == 0:
        size = sum(f.stat().st_size for f in RUNTIME.rglob("*") if f.is_file()) / 1024 / 1024
        print(f"[完成] runtime 就绪，体积 {size:.1f} MB")
    else:
        print("[失败] 依赖导入校验未通过，请检查上面的输出")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
