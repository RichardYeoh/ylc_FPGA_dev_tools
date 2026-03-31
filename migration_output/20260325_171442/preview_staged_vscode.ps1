param([string]$OpenPath = ".")

# Launch the staged VS Code environment without touching the real user profile / 启动隔离的 VS Code 预览环境，不修改真实用户配置
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$userDataDir = Join-Path $scriptRoot "staged_user_data_Antigravity_Migration"
code --user-data-dir $userDataDir $OpenPath
