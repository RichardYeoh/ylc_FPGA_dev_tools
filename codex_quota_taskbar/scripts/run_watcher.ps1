$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
. "$PSScriptRoot\resolve_runtime.ps1"
$LogPath = Join-Path $ProjectRoot "watcher_startup.log"

function Write-WatcherStartupLog {
    param([string]$Message)
    try {
        Add-Content -LiteralPath $LogPath -Value ((Get-Date).ToUniversalTime().ToString("o") + " " + $Message) -Encoding UTF8
    } catch {
        $null = $_
    }
}

# Start the Codex process watcher / 启动 Codex 进程监听器
try {
    $PythonwExe = Resolve-CodexPythonw
    $WatcherPath = Join-Path $ProjectRoot "src\codex_quota_watcher.py"
    $Process = Start-Process -FilePath $PythonwExe -ArgumentList "`"$WatcherPath`"" -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
    Write-WatcherStartupLog ("started pid=" + $Process.Id + " python=" + $PythonwExe)
} catch {
    Write-WatcherStartupLog ("start_failed " + $_.Exception.Message)
    exit 1
}
