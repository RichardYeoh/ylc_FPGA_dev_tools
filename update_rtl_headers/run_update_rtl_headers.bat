@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo RTL header normalization started
echo Workspace: %cd%
echo Target   : .\rtl
echo Mode     : apply changes and verify automatically
echo ============================================================
echo.

python .\update_rtl_headers.py --apply .\rtl
if errorlevel 1 (
    echo.
    echo [ERROR] Apply step failed.
    goto end
)

echo.
echo ------------------------------------------------------------
echo Verification pass
echo ------------------------------------------------------------
python .\update_rtl_headers.py .\rtl
if errorlevel 1 (
    echo.
    echo [ERROR] Verification step failed.
    goto end
)

echo.
echo ============================================================
echo Completed. Review the output above before closing this window.
echo ============================================================

:end
echo.
pause
