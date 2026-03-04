@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0gen_my_sim.ps1" %*
exit /b %ERRORLEVEL%

