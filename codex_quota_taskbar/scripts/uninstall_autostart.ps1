param(
    [string]$TaskName = "CodexQuotaTaskbarWatcher"
)

$ErrorActionPreference = "Stop"

# Remove the per-user logon task / 删除当前用户登录启动任务
try {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction Stop
        Write-Host "Removed scheduled task: $TaskName"
    } else {
        Write-Host "Scheduled task not found: $TaskName"
    }
} catch {
    Write-Warning "Scheduled task removal failed: $($_.Exception.Message)"
}

# Remove the Startup shortcut fallback / 删除启动文件夹快捷方式回退项
$StartupPath = [Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupPath "$TaskName.lnk"
if (Test-Path -LiteralPath $ShortcutPath) {
    Remove-Item -LiteralPath $ShortcutPath -Force
    Write-Host "Removed Startup shortcut: $ShortcutPath"
} else {
    Write-Host "Startup shortcut not found: $ShortcutPath"
}
