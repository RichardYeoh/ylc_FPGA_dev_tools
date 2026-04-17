@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

python .\remove_debug_flags.py --gui
