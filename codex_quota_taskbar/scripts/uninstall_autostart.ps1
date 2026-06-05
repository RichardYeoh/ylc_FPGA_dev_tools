param(
    [string]$TaskName = "CodexQuotaTaskbarWatcher"
)

$ErrorActionPreference = "Stop"

# Remove the per-user logon task / 删除当前用户登录启动任务
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "Removed scheduled task: $TaskName"
} else {
    Write-Host "Scheduled task not found: $TaskName"
}
