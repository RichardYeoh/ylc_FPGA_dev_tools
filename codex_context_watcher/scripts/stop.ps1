$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Watcher = Join-Path $ProjectRoot 'src\codex_context_watcher.py'
& python $Watcher stop
exit $LASTEXITCODE
