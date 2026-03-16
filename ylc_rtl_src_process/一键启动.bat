@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

python .\rtl_src_process_tool.py
