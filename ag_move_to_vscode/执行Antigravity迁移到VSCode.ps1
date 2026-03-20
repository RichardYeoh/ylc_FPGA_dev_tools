param(
    [switch]$ApplyConfig,
    [switch]$GenerateExtensionInstallScript,
    [string]$ProfileName = "Antigravity Migration",
    [string]$BackupRoot = ".\\migration_backups",
    [string]$OutputRoot = ".\\migration_output"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Copy-IfExists {
    param(
        [string]$Source,
        [string]$Destination
    )
    if (-not (Test-Path $Source)) {
        return $false
    }

    $parent = Split-Path -Parent $Destination
    if ($parent) {
        Ensure-Dir -Path $parent
    }

    try {
        $sourceItem = Get-Item -LiteralPath $Source
        if ($sourceItem.PSIsContainer) {
            Ensure-Dir -Path $Destination
            $null = & robocopy $Source $Destination /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP
            if ($LASTEXITCODE -ge 8) {
                return $false
            }
        } else {
            Copy-Item -Path $Source -Destination $Destination -Force
        }
        return $true
    } catch {
        return $false
    }
}

function Write-Utf8File {
    param(
        [string]$Path,
        [string]$Content
    )
    $parent = Split-Path -Parent $Path
    if ($parent) {
        Ensure-Dir -Path $parent
    }
    Set-Content -Path $Path -Value $Content -Encoding UTF8
}

function Get-ExtensionIds {
    param([string]$ExtensionsJsonPath)
    if (-not (Test-Path $ExtensionsJsonPath)) {
        return @()
    }

    $raw = Get-Content -Path $ExtensionsJsonPath -Raw -Encoding UTF8
    $items = $raw | ConvertFrom-Json
    return $items | ForEach-Object { $_.identifier.id } | Sort-Object -Unique
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$cwd = (Get-Location).Path
$backupRootAbs = Join-Path $cwd $BackupRoot
$outputRootAbs = Join-Path $cwd $OutputRoot
$backupDir = Join-Path $backupRootAbs $timestamp
$runDir = Join-Path $outputRootAbs $timestamp

Ensure-Dir -Path $backupDir
Ensure-Dir -Path $runDir

$agUserDir = Join-Path $env:APPDATA "Antigravity\\User"
$agExtDir = Join-Path $env:USERPROFILE ".antigravity\\extensions"
$agExtJson = Join-Path $agExtDir "extensions.json"
$vsUserDir = Join-Path $env:APPDATA "Code\\User"
$vsExtDir = Join-Path $env:USERPROFILE ".vscode\\extensions"

$settingsSrc = Join-Path $agUserDir "settings.json"
$keybindingsSrc = Join-Path $agUserDir "keybindings.json"
$snippetsSrc = Join-Path $agUserDir "snippets"

$settingsDst = Join-Path $vsUserDir "settings.json"
$keybindingsDst = Join-Path $vsUserDir "keybindings.json"
$snippetsDst = Join-Path $vsUserDir "snippets"

$backupItems = @(
    @{ Source = $agUserDir; Destination = Join-Path $backupDir "Antigravity_User" },
    @{ Source = $agExtDir; Destination = Join-Path $backupDir "Antigravity_extensions" },
    @{ Source = $vsUserDir; Destination = Join-Path $backupDir "VSCode_User_before" },
    @{ Source = $vsExtDir; Destination = Join-Path $backupDir "VSCode_extensions_before" }
)

$backupLog = foreach ($item in $backupItems) {
    [PSCustomObject]@{
        Source = $item.Source
        Destination = $item.Destination
        Copied = (Copy-IfExists -Source $item.Source -Destination $item.Destination)
    }
}

$extensionIds = @(Get-ExtensionIds -ExtensionsJsonPath $agExtJson)
$skipExtensions = @("jlcodes.antigravity-cockpit")
$installExtensions = @($extensionIds | Where-Object { $_ -notin $skipExtensions })

$extScript = @()
$extScript += "# Install VS Code extensions migrated from Antigravity"
$extScript += '$exts = @('
foreach ($ext in $installExtensions) {
    $extScript += "    `"$ext`","
}
if ($installExtensions.Count -gt 0) {
    $extScript[$extScript.Count - 1] = $extScript[$extScript.Count - 1].TrimEnd(",")
}
$extScript += ")"
$extScript += ""
$extScript += 'foreach ($ext in $exts) {'
$extScript += '    code --install-extension $ext'
$extScript += '}'

$extensionScriptPath = Join-Path $runDir "install_vscode_extensions.ps1"
Write-Utf8File -Path $extensionScriptPath -Content ($extScript -join "`r`n")

$configLog = @()
if ($ApplyConfig) {
    $configLog += [PSCustomObject]@{ Item = "settings.json"; Copied = (Copy-IfExists -Source $settingsSrc -Destination $settingsDst) }
    $configLog += [PSCustomObject]@{ Item = "keybindings.json"; Copied = (Copy-IfExists -Source $keybindingsSrc -Destination $keybindingsDst) }
    $configLog += [PSCustomObject]@{ Item = "snippets"; Copied = (Copy-IfExists -Source $snippetsSrc -Destination $snippetsDst) }
}

$summary = @()
$summary += "# Migration Summary"
$summary += ""
$summary += "## Mode"
$summary += ""
$summary += "- ApplyConfig: $ApplyConfig"
$summary += "- GenerateExtensionInstallScript: $GenerateExtensionInstallScript"
$summary += "- ProfileName: $ProfileName"
$summary += "- BackupDir: $backupDir"
$summary += "- RunDir: $runDir"
$summary += ""
$summary += "## Backups"
$summary += ""
foreach ($entry in $backupLog) {
    $summary += "- Source: $($entry.Source) | Copied: $($entry.Copied)"
}
$summary += ""
$summary += "## Extensions"
$summary += ""
$summary += "- Total Antigravity extensions: $($extensionIds.Count)"
$summary += "- Planned VS Code installs: $($installExtensions.Count)"
$summary += "- Skipped product-specific extensions: $($skipExtensions.Count)"
$summary += "- Generated installer script: $extensionScriptPath"
$summary += ""
$summary += "## Config Copy"
$summary += ""
if ($ApplyConfig) {
    foreach ($entry in $configLog) {
        $summary += "- $($entry.Item): $($entry.Copied)"
    }
} else {
    $summary += "- No VS Code user config was copied in this run."
    $summary += "- Re-run with -ApplyConfig to copy settings, keybindings, and snippets."
}
$summary += ""
$summary += "## Manual Checks"
$summary += ""
$summary += "- Remove or replace Antigravity-only settings such as agCockpit.*."
$summary += "- Review formatter paths that still point into the Antigravity install directory."
$summary += "- Verify whether mshr-h.veriloghdl is still the intended formatter."
$summary += "- Reinstall any .vsix-only extensions manually if Marketplace install fails."
$summary += "- Product-specific Antigravity features cannot be migrated 1:1."

$summaryPath = Join-Path $runDir "Migration_Summary.md"
Write-Utf8File -Path $summaryPath -Content ($summary -join "`r`n")

$walkthrough = @()
$walkthrough += "# Walkthrough"
$walkthrough += ""
$walkthrough += "## What this script does"
$walkthrough += ""
$walkthrough += "- Backs up Antigravity and VS Code user data."
$walkthrough += "- Reads the Antigravity extension inventory."
$walkthrough += "- Generates a VS Code extension install script."
$walkthrough += "- Optionally copies settings, keybindings, and snippets into VS Code."
$walkthrough += "- Produces a migration summary with manual follow-up items."
$walkthrough += ""
$walkthrough += "## Suggested usage"
$walkthrough += ""
$walkthrough += "1. Run once without parameters."
$walkthrough += "2. Review Migration_Summary.md."
$walkthrough += "3. Fix or confirm the manual checks."
$walkthrough += "4. Re-run with -ApplyConfig when ready."
$walkthrough += "5. Run install_vscode_extensions.ps1."

$walkthroughPath = Join-Path $runDir "Walkthrough.md"
Write-Utf8File -Path $walkthroughPath -Content ($walkthrough -join "`r`n")

Write-Host "Migration package generated at: $runDir"
Write-Host "Summary file: $summaryPath"
