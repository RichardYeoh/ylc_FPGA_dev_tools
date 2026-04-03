@echo off
setlocal
where pwsh >nul 2>nul
if "%ERRORLEVEL%"=="0" (
  pwsh -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0gen_my_sim.ps1" %*
) else (
  powershell -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0gen_my_sim.ps1" %*
)
exit /b %ERRORLEVEL%
