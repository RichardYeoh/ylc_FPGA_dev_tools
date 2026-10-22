@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem 优先使用打包好的 exe（发行包形态）
if exist "office2md.exe" (
    start "" "office2md.exe"
    exit /b 0
)

rem 源码形态：优先用随包的嵌入式运行时，其次用系统 Python
if exist "app.py" (
    if exist "runtime\python.exe" (
        "runtime\python.exe" "app.py" %*
        exit /b %errorlevel%
    )
    where python >nul 2>nul
    if errorlevel 1 (
        echo [错误] 当前目录既没有 office2md.exe，也没有可用的 Python 环境。
        echo         请把本文件放在发行包根目录（与 office2md.exe 同级）后再运行。
        pause
        exit /b 1
    )
    python "app.py" %*
    exit /b %errorlevel%
)

echo [错误] 找不到 office2md.exe 或 app.py。
echo         当前目录：%CD%
pause
exit /b 1
