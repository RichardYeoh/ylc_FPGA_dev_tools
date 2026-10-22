@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if "%~1"=="" (
    echo 用法：把 Word / Excel / PPT 文件或整个文件夹拖到本文件图标上松手。
    echo       转换结果 .md 会输出到源文件所在目录。
    echo       需要指定输出目录时，请改用图形界面（启动转换工具.bat）。
    echo.
    pause
    exit /b 1
)

if exist "office2md-cli.exe" (
    "office2md-cli.exe" %*
    goto done
)
if exist "runtime\python.exe" (
    if exist "app.py" (
        "runtime\python.exe" "app.py" %*
        goto done
    )
)
if exist "app.py" (
    python "app.py" %*
    goto done
)

echo [错误] 找不到 office2md-cli.exe 或 app.py。
echo         当前目录：%CD%

:done
echo.
echo 转换结束，按任意键关闭窗口。
pause >nul
