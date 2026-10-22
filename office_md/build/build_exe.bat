@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

echo ============================================
echo  office_md 一键打包（开发机执行）
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python，请先在开发机安装 Python 3.13 x64。
    pause
    exit /b 1
)

echo [1/3] 从 vendor\wheels 离线安装依赖……
python -m pip install --no-index --find-links=vendor\wheels -r requirements.txt -r requirements-build.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败。
    pause
    exit /b 1
)

echo.
echo [2/3] PyInstaller 打包……
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build\work build\office2md.spec
if errorlevel 1 (
    echo [错误] 打包失败。
    pause
    exit /b 1
)

echo.
echo [3/3] 组装发行目录……
python tools\make_release.py
if errorlevel 1 (
    echo [错误] 发行目录组装失败。
    pause
    exit /b 1
)

echo.
echo 全部完成，产物位于 dist\ 目录。
pause
