param(
    [string]$TaskName = "CodexQuotaTaskbarWatcher"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\resolve_runtime.ps1"
$PowerShellExe = Resolve-CodexPowerShell

# Register a per-user logon task first / 优先注册当前用户登录时启动的计划任务
$RunWatcher = Join-Path $ProjectRoot "scripts\run_watcher.ps1"
$Action = New-ScheduledTaskAction -Execute $PowerShellExe -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunWatcher`"" -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Launch Codex quota compact taskbar watcher" -Force -ErrorAction Stop | Out-Null
    Write-Host "Installed scheduled task: $TaskName"
    return
} catch {
    Write-Warning "Scheduled task install failed, falling back to Startup shortcut: $($_.Exception.Message)"
}

# Fallback to the current user's Startup folder / 回退到当前用户启动文件夹快捷方式
$StartupPath = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupPath "$TaskName.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $PowerShellExe
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$RunWatcher`""
$Shortcut.WorkingDirectory = $ProjectRoot
$Shortcut.WindowStyle = 7
$Shortcut.Description = "Launch Codex quota compact taskbar watcher"
$Shortcut.Save()
Write-Host "Installed Startup shortcut: $ShortcutPath"
