$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = (Get-Command python -ErrorAction Stop).Source
$PythonwExe = Join-Path (Split-Path -Parent $PythonExe) "pythonw.exe"
if (-not (Test-Path -LiteralPath $PythonwExe)) {
    $PythonwExe = $PythonExe
}

# Restart the compact UI so a hidden stale window is recovered / 重启紧凑 UI 以恢复隐藏的旧窗口
$Processes = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like "python*.exe" -and
    $_.CommandLine -like "*codex_quota_taskbar.py*" -and
    $_.CommandLine -like "*$ProjectRoot*"
}

$Processes | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force
}

Start-Process -FilePath $PythonwExe -ArgumentList "`"$ProjectRoot\src\codex_quota_taskbar.py`"" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
