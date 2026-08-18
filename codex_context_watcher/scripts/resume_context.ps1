$ResumeArgs = @($args)
if ($ResumeArgs.Count -lt 1) {
    Write-Error 'Usage: resume_context.ps1 <512k|1m> [resume arguments] / 用法：resume_context.ps1 <512k|1m> [恢复参数]'
    exit 2
}

$Tier = ([string]$ResumeArgs[0]).ToLowerInvariant()
switch ($Tier) {
    '512k' {
        $ContextWindow = 512000
        $CompactLimit = 430000
    }
    '1m' {
        $ContextWindow = 1000000
        $CompactLimit = 820000
    }
    default {
        Write-Error "Unsupported resume tier: $Tier / 不支持的恢复窗口档位：$Tier"
        exit 2
    }
}

$CodexCommand = Get-Command codex -ErrorAction SilentlyContinue
if ($null -eq $CodexCommand) {
    Write-Error 'Codex CLI was not found in PATH / PATH 中未找到 Codex CLI'
    exit 1
}

$ForwardArgs = @()
if ($ResumeArgs.Count -gt 1) {
    $ForwardArgs = @($ResumeArgs[1..($ResumeArgs.Count - 1)])
}

$CodexArgs = @(
    '-c', "model_context_window=$ContextWindow",
    '-c', "model_auto_compact_token_limit=$CompactLimit",
    'resume'
) + $ForwardArgs

& $CodexCommand.Source @CodexArgs
exit $LASTEXITCODE
