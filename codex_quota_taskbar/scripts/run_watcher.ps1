$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExe = (Get-Command python -ErrorAction Stop).Source
$PythonwExe = Join-Path (Split-Path -Parent $PythonExe) "pythonw.exe"
if (-not (Test-Path -LiteralPath $PythonwExe)) {
    $PythonwExe = $PythonExe
}

# Start the Codex process watcher / 启动 Codex 进程监听器
Start-Process -FilePath $PythonwExe -ArgumentList "`"$ProjectRoot\src\codex_quota_watcher.py`"" -WorkingDirectory $ProjectRoot -WindowStyle Hidden
