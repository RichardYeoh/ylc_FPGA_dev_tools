@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

python .\update_rtl_headers.py --gui
