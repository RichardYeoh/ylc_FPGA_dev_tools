# -*- coding: utf-8 -*-
"""把 PyInstaller 产物组装成统一 release 包。

产物结构：
    dist/office2md-<ver>/
        office2md-<ver>-win64/          exe 版（双击即用）
        office2md-<ver>-src-portable/   源码便携版（自带 Python 运行时）
        选择说明.txt                    两版差异与选用建议
    dist/office2md-<ver>.zip            上者整体压缩

用法：
    python tools/make_release.py

前置：python -m PyInstaller --noconfirm --distpath dist --workpath build/work build/office2md.spec
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
SRC_BUILD = DIST / "office2md"

REQUIRED = ["office2md.exe", "office2md-cli.exe", "_internal"]
DOCS = ("使用说明书.md", "软件设计书.md", "迁移部署说明.md")
LAUNCHERS = ("启动转换工具.bat", "拖放文件转换.bat")

PICK_NOTE = """office_md {ver} 发行包说明
========================================

本包内含两个版本，功能完全一致、代码同源，按需选一个使用：

1) office2md-{ver}-win64\\           【推荐】exe 版
   - 构成：office2md.exe / office2md-cli.exe / _internal
   - 体积：约 65 MB
   - 启动：双击 office2md.exe 或「启动转换工具.bat」
   - 适合：日常使用，不关心源码
   - 优点：启动快、目录干净

2) office2md-{ver}-src-portable\\   源码便携版
   - 构成：app.py / src / runtime（Python 3.13 嵌入式 + 离线依赖）
   - 体积：约 85 MB
   - 启动：双击「启动转换工具.bat」（自动使用 runtime\\python.exe）
   - 适合：需要二次开发、改转换规则
   - 优点：改完 src 下的 .py 立即生效，无需重新打包

注意事项
----------------------------------------
* 两版请解压到不同目录，不要混放。
* 程序目录需可写（日志、临时文件写在程序目录内）。
* 运行要求：Windows 10/11 x64；转换 .doc/.ppt/.xls 需本机安装 Microsoft Office。
* 运行期完全离线，不需要网络。
* 内附 docs：使用说明书 / 软件设计书 / 迁移部署说明。
* 交付前请按「迁移部署说明」第 4 节做一次自检。
"""


def main() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    from office2md import __version__

    release_root = DIST / f"office2md-{__version__}"
    if "--zip-only" in sys.argv:
        if not release_root.exists():
            print(f"[错误] 未找到 release 目录：{release_root}")
            return 1
        _make_zip(release_root)
        return 0

    release_root.mkdir(parents=True, exist_ok=True)
    target = release_root / f"office2md-{__version__}-win64"

    # ---------- 1. exe 版 ----------
    if SRC_BUILD.exists():
        missing = [n for n in REQUIRED if not (SRC_BUILD / n).exists()]
        if missing:
            print(f"[错误] 打包产物不完整，缺少：{', '.join(missing)}")
            return 1
        print(f"[1/3] 复制 exe 版 → {target.name}")
        # dirs_exist_ok：增量覆盖，避免删除上千文件触发批量删除保护
        shutil.copytree(SRC_BUILD, target, dirs_exist_ok=True)
    elif target.exists() and (target / "office2md.exe").exists():
        print("[1/3] 未找到 PyInstaller 产物，沿用已有 exe 版目录，仅刷新文档/样例")
    else:
        print(f"[错误] 未找到打包产物：{SRC_BUILD}")
        print("        请先执行 build\\build_exe.bat")
        return 1

    _copy_common(target, __version__, kind="exe")

    # ---------- 2. 源码便携版 ----------
    portable = build_src_portable(__version__, release_root)
    if portable is None:
        print("[2/3] 跳过源码便携版")

    # ---------- 3. 说明 + 压缩 ----------
    note = release_root / "选择说明.txt"
    note.write_text(PICK_NOTE.format(ver=__version__), encoding="utf-8")
    print(f"[3/3] 生成 {note.name}")

    _make_zip(release_root)
    return 0


def _make_zip(release_root: Path) -> Path:
    size_mb = sum(f.stat().st_size for f in release_root.rglob("*") if f.is_file()) / 1024 / 1024
    print(f"      正在压缩 {release_root.name}（约 {size_mb:.0f} MB）……")
    archive = shutil.make_archive(
        str(release_root), "zip", root_dir=str(release_root.parent), base_dir=release_root.name
    )
    zip_mb = Path(archive).stat().st_size / 1024 / 1024
    print("")
    print(f"[完成] release 目录：{release_root}  ({size_mb:.1f} MB)")
    print(f"[完成] release 压缩包：{archive}  ({zip_mb:.1f} MB)")
    return Path(archive)


def _copy_common(target: Path, version: str, kind: str) -> None:
    """把启动脚本、文档、样例、版本信息复制进发行目录。"""
    for name in LAUNCHERS:
        src = ROOT / name
        if src.exists():
            shutil.copy2(src, target / name)
        else:
            print(f"[警告] 缺少启动脚本：{name}")

    for name in DOCS:
        src = ROOT / "docs" / name
        if src.exists():
            shutil.copy2(src, target / name)
        else:
            print(f"[警告] 缺少文档：docs/{name}")

    samples = ROOT / "samples"
    if samples.exists():
        shutil.copytree(samples, target / "samples", dirs_exist_ok=True)

    if kind == "exe":
        text = (
            f"office_md 版本：{version}（exe 版）\n"
            "构建方式：PyInstaller onedir（Python 3.13 / Windows x64）\n"
            "运行要求：Windows 10/11 x64；转换老格式 .doc/.ppt/.xls 需本机安装 Microsoft Office\n"
            "网络要求：无（完全离线）\n"
            "启动方式：双击 office2md.exe 或「启动转换工具.bat」\n"
            "迁移方式：整个目录拷贝到目标机即可，无需安装\n"
        )
        (target / "版本信息.txt").write_text(text, encoding="utf-8")


def build_src_portable(version: str, release_root: Path):
    """源码 + 嵌入式 Python 运行时 + bat，供二次开发或在无 Python 的机器上跑源码。"""
    runtime = ROOT / "runtime"
    if not (runtime / "python.exe").exists():
        print("[2/3] 未找到 runtime\\python.exe，跳过源码便携版")
        return None

    target = release_root / f"office2md-{version}-src-portable"
    print(f"[2/3] 组装源码便携版 → {target.name}")
    shutil.copytree(runtime, target / "runtime", dirs_exist_ok=True)
    shutil.copytree(ROOT / "src", target / "src", dirs_exist_ok=True)
    shutil.copy2(ROOT / "app.py", target / "app.py")
    _copy_common(target, version, kind="src")

    (target / "版本信息.txt").write_text(
        f"office_md 版本：{version}（源码便携版）\n"
        "构成：Python 3.13 嵌入式运行时 + 源码 + 离线依赖 site-packages\n"
        "启动：双击「启动转换工具.bat」（自动使用 runtime\\python.exe）\n"
        "用途：二次开发、调试、无 Python 环境下的源码运行\n"
        "运行要求：Windows 10/11 x64；老格式需本机安装 Microsoft Office\n"
        "修改代码：直接改 src\\office2md\\*.py，重新双击 bat 即生效\n",
        encoding="utf-8",
    )
    return target


if __name__ == "__main__":
    raise SystemExit(main())
