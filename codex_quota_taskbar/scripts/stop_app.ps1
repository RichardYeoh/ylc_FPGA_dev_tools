$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot

# Stop only this project's compact UI / 仅停止本项目的紧凑显示 UI
$Processes = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -like "python*.exe" -and
    $_.CommandLine -like "*codex_quota_taskbar.py*" -and
    $_.CommandLine -like "*$ProjectRoot*"
}

$Processes | ForEach-Object {
    Stop-Process -Id $_.ProcessId -Force
}
