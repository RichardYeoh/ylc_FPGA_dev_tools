@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."

echo 重建 runtime\（源码便携版运行时）
echo 前提：本机装有 Python 3.13 x64，且 vendor\ 下的运行时压缩包与 wheel 齐全。
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 python。
    pause
    exit /b 1
)

python tools\build_runtime.py
if errorlevel 1 (
    echo.
    echo [失败] 重建未完成，请查看上面的输出。
    pause
    exit /b 1
)

echo.
pause
