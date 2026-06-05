param(
    [string]$TaskName = "CodexQuotaTaskbarWatcher"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = (Get-Command python -ErrorAction Stop).Source
$PythonwExe = Join-Path (Split-Path -Parent $PythonExe) "pythonw.exe"
if (-not (Test-Path -LiteralPath $PythonwExe)) {
    $PythonwExe = $PythonExe
}

# Register a per-user logon task / 注册当前用户登录时启动的任务
$Watcher = Join-Path $ProjectRoot "src\codex_quota_watcher.py"
$Action = New-ScheduledTaskAction -Execute $PythonwExe -Argument "`"$Watcher`"" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Launch Codex quota compact taskbar watcher" -Force | Out-Null
Write-Host "Installed scheduled task: $TaskName"
