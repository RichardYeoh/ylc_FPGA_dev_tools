@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo ============================================================
echo  office_md 清理可再生产物
echo ============================================================
echo.
echo 将要删除：
echo   dist\office2md              PyInstaller 原始输出（可用 build\build_exe.bat 重新生成）
echo   dist\office2md_prev         旧的不完整打包产物
echo   build\work                  打包缓存
echo   logs\  temp\                运行日志与临时文件
echo   各级 __pycache__            Python 字节码缓存
echo.
echo 不会删除（保留）：
echo   src\  docs\  tools\  samples*\  vendor\  runtime\
echo   dist\office2md-1.0.0-win64\           exe 发行包
echo   dist\office2md-1.0.0-src-portable\    源码便携版
echo   dist\*.zip                            发行压缩包
echo.

set /p ok=确认清理？(Y/N):
if /i not "%ok%"=="Y" (
    echo 已取消，未做任何改动。
    pause
    exit /b 0
)

echo.
echo [1/5] 删除 dist\office2md ...
if exist "dist\office2md" rd /s /q "dist\office2md"

echo [2/5] 删除 dist\office2md_prev ...
if exist "dist\office2md_prev" rd /s /q "dist\office2md_prev"

echo [3/5] 删除 build\work ...
if exist "build\work" rd /s /q "build\work"

echo [4/5] 删除 logs / temp ...
if exist "logs" rd /s /q "logs"
if exist "temp" rd /s /q "temp"

echo [5/5] 删除源码与运行时里的 __pycache__ ...
for /d /r "src" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r "tools" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"
for /d /r "runtime" %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d"

echo.
echo 清理完成。当前目录：
dir /b

echo.
pause
