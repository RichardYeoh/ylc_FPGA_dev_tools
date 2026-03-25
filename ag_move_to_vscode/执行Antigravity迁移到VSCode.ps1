param(
    [switch]$ApplyConfig,
    [switch]$GenerateExtensionInstallScript,
    [switch]$InstallExtensions,
    [switch]$IncludeExtensionArtifacts,
    [switch]$SkipBackups,
    [string]$ProfileName = "Antigravity Migration",
    [string]$VeribleFormatterPath = "",
    [string]$PreferredVerilogFormatter = "",
    [string]$TargetUserDir = "",
    [string]$BackupRoot = ".\migration_backups",
    [string]$OutputRoot = ".\migration_output"
)

$ErrorActionPreference = "Stop"

function Ensure-Dir {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType Directory -Path $Path | Out-Null
    }
}

function Copy-IfExists {
    param(
        [string]$Source,
        [string]$Destination
    )

    if (-not (Test-Path -LiteralPath $Source)) {
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
            Copy-Item -LiteralPath $Source -Destination $Destination -Force
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

function Escape-JsonString {
    param([string]$Value)

    if ($null -eq $Value) {
        return ""
    }

    return $Value.Replace('\', '\\').Replace('"', '\"')
}

function Get-ExtensionRecords {
    param([string]$ExtensionsJsonPath)

    if (-not (Test-Path -LiteralPath $ExtensionsJsonPath)) {
        return @()
    }

    $raw = Get-Content -Path $ExtensionsJsonPath -Raw -Encoding UTF8
    $items = $raw | ConvertFrom-Json
    $records = @()

    foreach ($item in $items) {
        $sourceType = "unknown"
        if ($item.metadata -and $item.metadata.source) {
            $sourceType = [string]$item.metadata.source
        }

        $records += [PSCustomObject]@{
            Id               = [string]$item.identifier.id
            Version          = [string]$item.version
            RelativeLocation = [string]$item.relativeLocation
            SourceType       = $sourceType
        }
    }

    return $records | Sort-Object Id -Unique
}

function Invoke-SettingsMigration {
    param(
        [string]$SourcePath,
        [string]$DestinationPath,
        [string[]]$InstalledExtensionIds,
        [string]$VeribleFormatterPath,
        [string]$PreferredVerilogFormatter
    )

    $result = [PSCustomObject]@{
        SourceExists          = $false
        DestinationPath       = $DestinationPath
        RemovedKeys           = @()
        UpdatedItems          = @()
        Warnings              = @()
        FormatterReviewNeeded = $false
    }

    if (-not (Test-Path -LiteralPath $SourcePath)) {
        return $result
    }

    $result.SourceExists = $true
    $lines = Get-Content -Path $SourcePath -Encoding UTF8
    $installed = @{}

    foreach ($id in $InstalledExtensionIds) {
        if ($id) {
            $installed[$id.ToLowerInvariant()] = $true
        }
    }

    $outputLines = New-Object System.Collections.Generic.List[string]
    $removedKeys = New-Object System.Collections.Generic.List[string]
    $updatedItems = New-Object System.Collections.Generic.List[string]
    $warnings = New-Object System.Collections.Generic.List[string]
    $formatterReviewNeeded = -not $installed.ContainsKey("mshr-h.veriloghdl")

    foreach ($line in $lines) {
        if ($line -match '^\s*"(?<key>agCockpit\.[^"]+)"\s*:') {
            $key = $Matches["key"]
            $removedKeys.Add($key) | Out-Null
            $outputLines.Add("    // Removed during migration because VS Code does not use this Antigravity-only setting / 迁移时移除，VS Code 不使用该 Antigravity 专有设置: $key") | Out-Null
            continue
        }

        if ($line -match '^(?<indent>\s*)"verilog\.formatting\.veribleVerilogFormatter\.path"\s*:\s*"(?<value>[^"]*)"(?<suffix>\s*,?\s*)$') {
            $indent = $Matches["indent"]
            $currentValue = $Matches["value"]
            $suffix = $Matches["suffix"]

            if ($VeribleFormatterPath) {
                $escapedPath = Escape-JsonString -Value $VeribleFormatterPath
                $outputLines.Add($indent + '"verilog.formatting.veribleVerilogFormatter.path": "' + $escapedPath + '"' + $suffix) | Out-Null
                $updatedItems.Add("Replaced verible formatter path / 已替换 Verible 格式化器路径: $VeribleFormatterPath") | Out-Null

                if (-not (Test-Path -LiteralPath $VeribleFormatterPath)) {
                    $warnings.Add("Replacement verible formatter path does not exist yet / 替换后的 Verible 路径当前不存在: $VeribleFormatterPath") | Out-Null
                }
            } elseif ($currentValue -like '*Antigravity*verible-verilog-format.exe*') {
                $warnings.Add("Verible formatter path still points to Antigravity / Verible 路径仍指向 Antigravity: $currentValue") | Out-Null
                $outputLines.Add($indent + '// REVIEW: replace before uninstalling Antigravity / 卸载 Antigravity 前请替换此路径') | Out-Null
                $outputLines.Add($line) | Out-Null
            } else {
                $outputLines.Add($line) | Out-Null
            }

            continue
        }

        if ($line -match '^(?<indent>\s*)"editor\.defaultFormatter"\s*:\s*"mshr-h\.veriloghdl"(?<suffix>\s*,?\s*)$') {
            $indent = $Matches["indent"]
            $suffix = $Matches["suffix"]

            if ($PreferredVerilogFormatter) {
                $escapedFormatter = Escape-JsonString -Value $PreferredVerilogFormatter
                $outputLines.Add($indent + '"editor.defaultFormatter": "' + $escapedFormatter + '"' + $suffix) | Out-Null
                $updatedItems.Add("Replaced mshr-h.veriloghdl with preferred formatter / 已将 mshr-h.veriloghdl 替换为指定 formatter: $PreferredVerilogFormatter") | Out-Null
            } else {
                if ($formatterReviewNeeded) {
                    $warnings.Add("Formatter mshr-h.veriloghdl is not present in the current extension inventory / 当前扩展清单中未发现 mshr-h.veriloghdl") | Out-Null
                    $outputLines.Add($indent + '// REVIEW: formatter extension mshr-h.veriloghdl was not found in the current Antigravity extension inventory / 当前 Antigravity 扩展清单未发现该 formatter 扩展') | Out-Null
                }
                $outputLines.Add($line) | Out-Null
            }

            continue
        }

        $outputLines.Add($line) | Out-Null
    }

    Write-Utf8File -Path $DestinationPath -Content ($outputLines -join "`r`n")

    $result.RemovedKeys = @($removedKeys.ToArray())
    $result.UpdatedItems = @($updatedItems.ToArray())
    $result.Warnings = @($warnings.ToArray() | Sort-Object -Unique)
    $result.FormatterReviewNeeded = $formatterReviewNeeded
    return $result
}

function Copy-ExtensionsToStage {
    param(
        [object[]]$ExtensionRecords,
        [string]$SourceRoot,
        [string]$DestinationRoot,
        [string[]]$SkipIds
    )

    $skipMap = @{}
    foreach ($skipId in $SkipIds) {
        $skipMap[$skipId.ToLowerInvariant()] = $true
    }

    $logs = @()
    foreach ($record in $ExtensionRecords) {
        $copied = $false
        $skipped = $false
        $reason = ""
        $sourcePath = ""
        $destinationPath = ""

        if ($skipMap.ContainsKey($record.Id.ToLowerInvariant())) {
            $skipped = $true
            $reason = "product-specific"
        } elseif (-not $record.RelativeLocation) {
            $reason = "missing-relative-location"
        } else {
            $sourcePath = Join-Path $SourceRoot $record.RelativeLocation
            $destinationPath = Join-Path $DestinationRoot $record.RelativeLocation
            $copied = Copy-IfExists -Source $sourcePath -Destination $destinationPath
            if (-not $copied) {
                $reason = "copy-failed"
            }
        }

        $logs += [PSCustomObject]@{
            Id               = $record.Id
            Version          = $record.Version
            SourceType       = $record.SourceType
            RelativeLocation = $record.RelativeLocation
            Copied           = $copied
            Skipped          = $skipped
            Reason           = $reason
        }
    }

    return $logs
}

function Invoke-ExtensionInstall {
    param([string[]]$ExtensionIds)

    $results = @()
    foreach ($extensionId in $ExtensionIds) {
        $output = & code --install-extension $extensionId 2>&1
        $results += [PSCustomObject]@{
            Id      = $extensionId
            Success = ($LASTEXITCODE -eq 0)
            Output  = (($output | ForEach-Object { "$_" }) -join "`r`n")
        }
    }

    return $results
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$cwd = (Get-Location).Path
$profileSafeName = ($ProfileName -replace '[^A-Za-z0-9._-]', '_')
$backupRootAbs = Join-Path $cwd $BackupRoot
$outputRootAbs = Join-Path $cwd $OutputRoot
$backupDir = Join-Path $backupRootAbs $timestamp
$runDir = Join-Path $outputRootAbs $timestamp
$stagedUserDataDir = Join-Path $runDir ("staged_user_data_" + $profileSafeName)
$stagedUserDir = Join-Path $stagedUserDataDir "User"
$stagedExtensionsDir = Join-Path $runDir ("staged_extensions_" + $profileSafeName)

Ensure-Dir -Path $runDir
Ensure-Dir -Path $stagedUserDir
if ($IncludeExtensionArtifacts) {
    Ensure-Dir -Path $stagedExtensionsDir
}

$agUserDir = Join-Path $env:APPDATA "Antigravity\User"
$agExtDir = Join-Path $env:USERPROFILE ".antigravity\extensions"
$agExtJson = Join-Path $agExtDir "extensions.json"
$defaultVsUserDir = Join-Path $env:APPDATA "Code\User"
$defaultVsExtDir = Join-Path $env:USERPROFILE ".vscode\extensions"
$resolvedTargetUserDir = if ([string]::IsNullOrWhiteSpace($TargetUserDir)) { $defaultVsUserDir } else { $TargetUserDir }

$settingsSrc = Join-Path $agUserDir "settings.json"
$keybindingsSrc = Join-Path $agUserDir "keybindings.json"
$snippetsSrc = Join-Path $agUserDir "snippets"

$stagedSettingsDst = Join-Path $stagedUserDir "settings.json"
$stagedKeybindingsDst = Join-Path $stagedUserDir "keybindings.json"
$stagedSnippetsDst = Join-Path $stagedUserDir "snippets"

$targetSettingsDst = Join-Path $resolvedTargetUserDir "settings.json"
$targetKeybindingsDst = Join-Path $resolvedTargetUserDir "keybindings.json"
$targetSnippetsDst = Join-Path $resolvedTargetUserDir "snippets"

$backupLog = @()
if (-not $SkipBackups) {
    Ensure-Dir -Path $backupDir
    $backupItems = @(
        @{ Label = "Antigravity_settings.json"; Source = $settingsSrc; Destination = Join-Path $backupDir "Antigravity_User\settings.json" },
        @{ Label = "Antigravity_keybindings.json"; Source = $keybindingsSrc; Destination = Join-Path $backupDir "Antigravity_User\keybindings.json" },
        @{ Label = "Antigravity_snippets"; Source = $snippetsSrc; Destination = Join-Path $backupDir "Antigravity_User\snippets" },
        @{ Label = "Antigravity_extensions.json"; Source = $agExtJson; Destination = Join-Path $backupDir "Antigravity_extensions\extensions.json" },
        @{ Label = "VSCode_settings_before"; Source = $targetSettingsDst; Destination = Join-Path $backupDir "VSCode_User_before\settings.json" },
        @{ Label = "VSCode_keybindings_before"; Source = $targetKeybindingsDst; Destination = Join-Path $backupDir "VSCode_User_before\keybindings.json" },
        @{ Label = "VSCode_snippets_before"; Source = $targetSnippetsDst; Destination = Join-Path $backupDir "VSCode_User_before\snippets" }
    )

    if ($IncludeExtensionArtifacts) {
        $backupItems += @(
            @{ Label = "Antigravity_extensions"; Source = $agExtDir; Destination = Join-Path $backupDir "Antigravity_extensions_full" },
            @{ Label = "VSCode_extensions_before"; Source = $defaultVsExtDir; Destination = Join-Path $backupDir "VSCode_extensions_before" }
        )
    }

    foreach ($item in $backupItems) {
        $backupLog += [PSCustomObject]@{
            Label       = $item.Label
            Source      = $item.Source
            Destination = $item.Destination
            Copied      = (Copy-IfExists -Source $item.Source -Destination $item.Destination)
        }
    }
}

$extensionRecords = @(Get-ExtensionRecords -ExtensionsJsonPath $agExtJson)
$extensionIds = @($extensionRecords | ForEach-Object { $_.Id })
$skipExtensions = @("jlcodes.antigravity-cockpit")
$galleryExtensions = @($extensionRecords | Where-Object { $_.SourceType -eq "gallery" -and $_.Id -notin $skipExtensions })
$manualExtensions = @($extensionRecords | Where-Object { $_.SourceType -ne "gallery" -and $_.Id -notin $skipExtensions })
$stagedExtensionLog = @()
if ($IncludeExtensionArtifacts) {
    $stagedExtensionLog = Copy-ExtensionsToStage -ExtensionRecords $extensionRecords -SourceRoot $agExtDir -DestinationRoot $stagedExtensionsDir -SkipIds $skipExtensions
}

$stagedSettingsLog = Invoke-SettingsMigration `
    -SourcePath $settingsSrc `
    -DestinationPath $stagedSettingsDst `
    -InstalledExtensionIds $extensionIds `
    -VeribleFormatterPath $VeribleFormatterPath `
    -PreferredVerilogFormatter $PreferredVerilogFormatter

$stagedConfigLog = @(
    [PSCustomObject]@{ Item = "settings.json"; Target = $stagedSettingsDst; Copied = $stagedSettingsLog.SourceExists },
    [PSCustomObject]@{ Item = "keybindings.json"; Target = $stagedKeybindingsDst; Copied = (Copy-IfExists -Source $keybindingsSrc -Destination $stagedKeybindingsDst) },
    [PSCustomObject]@{ Item = "snippets"; Target = $stagedSnippetsDst; Copied = (Copy-IfExists -Source $snippetsSrc -Destination $stagedSnippetsDst) }
)

$applyLog = @()
if ($ApplyConfig) {
    Ensure-Dir -Path $resolvedTargetUserDir

    $appliedSettingsLog = Invoke-SettingsMigration `
        -SourcePath $settingsSrc `
        -DestinationPath $targetSettingsDst `
        -InstalledExtensionIds $extensionIds `
        -VeribleFormatterPath $VeribleFormatterPath `
        -PreferredVerilogFormatter $PreferredVerilogFormatter

    $applyLog += [PSCustomObject]@{ Item = "settings.json"; Target = $targetSettingsDst; Copied = $appliedSettingsLog.SourceExists }
    $applyLog += [PSCustomObject]@{ Item = "keybindings.json"; Target = $targetKeybindingsDst; Copied = (Copy-IfExists -Source $keybindingsSrc -Destination $targetKeybindingsDst) }
    $applyLog += [PSCustomObject]@{ Item = "snippets"; Target = $targetSnippetsDst; Copied = (Copy-IfExists -Source $snippetsSrc -Destination $targetSnippetsDst) }
}

$previewScriptLines = @(
    "param([string]`$OpenPath = `".`")",
    "",
    "# Launch the staged VS Code environment without touching the real user profile / 启动隔离的 VS Code 预览环境，不修改真实用户配置",
    "`$scriptRoot = Split-Path -Parent `$MyInvocation.MyCommand.Path",
    "`$userDataDir = Join-Path `$scriptRoot `"staged_user_data_$profileSafeName`""
)
$previewScriptLines += if ($IncludeExtensionArtifacts) {
    @(
        "`$extensionsDir = Join-Path `$scriptRoot `"staged_extensions_$profileSafeName`"",
        "code --user-data-dir `$userDataDir --extensions-dir `$extensionsDir `$OpenPath"
    )
} else {
    @(
        "code --user-data-dir `$userDataDir `$OpenPath"
    )
}
$previewScriptPath = Join-Path $runDir "preview_staged_vscode.ps1"
Write-Utf8File -Path $previewScriptPath -Content ($previewScriptLines -join "`r`n")

$galleryInstallScriptPath = ""
$manualExtensionNotesPath = ""
if ($GenerateExtensionInstallScript) {
    $galleryScript = @(
        "param(",
        "    [string]`$UserDataDir = `"`",",
        "    [string]`$ExtensionsDir = `"`"",
        ")",
        "",
        "# Install gallery extensions into the selected VS Code environment / 向指定 VS Code 环境安装来自 Marketplace 的扩展",
        "`$exts = @("
    )

    foreach ($record in $galleryExtensions) {
        $galleryScript += "    `"$($record.Id)`","
    }
    if ($galleryExtensions.Count -gt 0) {
        $galleryScript[$galleryScript.Count - 1] = $galleryScript[$galleryScript.Count - 1].TrimEnd(",")
    }
    $galleryScript += ")"
    $galleryScript += ""
    $galleryScript += "`$baseArgs = @()"
    $galleryScript += "if (`$UserDataDir) { `$baseArgs += '--user-data-dir'; `$baseArgs += `$UserDataDir }"
    $galleryScript += "if (`$ExtensionsDir) { `$baseArgs += '--extensions-dir'; `$baseArgs += `$ExtensionsDir }"
    $galleryScript += "foreach (`$ext in `$exts) {"
    $galleryScript += "    & code @baseArgs --install-extension `$ext"
    $galleryScript += "}"

    $galleryInstallScriptPath = Join-Path $runDir "install_gallery_extensions.ps1"
    Write-Utf8File -Path $galleryInstallScriptPath -Content ($galleryScript -join "`r`n")
}

$extensionInstallResults = @()
if ($InstallExtensions) {
    $extensionInstallResults = Invoke-ExtensionInstall -ExtensionIds @($galleryExtensions | ForEach-Object { $_.Id })
}

$manualExtensionListPath = Join-Path $runDir "VSCode_Extensions_Manual_Install.md"
$manualExtensionList = @()
$manualExtensionList += "# VS Code Extensions Manual Install List"
$manualExtensionList += ""
$manualExtensionList += "## Gallery Extensions"
$manualExtensionList += ""
foreach ($record in $galleryExtensions) {
    $manualExtensionList += "- $($record.Id)"
}
$manualExtensionList += ""
$manualExtensionList += "## VSIX Or Manual Extensions"
$manualExtensionList += ""
if ($manualExtensions.Count -eq 0) {
    $manualExtensionList += "- None"
} else {
    foreach ($record in $manualExtensions) {
        $manualExtensionList += "- $($record.Id) | source=$($record.SourceType) | relativeLocation=$($record.RelativeLocation)"
    }
}
$manualExtensionList += ""
$manualExtensionList += "## Skipped Product-Specific Extensions"
$manualExtensionList += ""
foreach ($skipId in $skipExtensions) {
    $manualExtensionList += "- $skipId"
}
Write-Utf8File -Path $manualExtensionListPath -Content ($manualExtensionList -join "`r`n")

if ($GenerateExtensionInstallScript) {
    $manualNotes = @()
    $manualNotes += "# Manual Extension Notes"
    $manualNotes += ""
    $manualNotes += "## Recommended Order"
    $manualNotes += ""
    $manualNotes += "1. Install the gallery extensions manually in VS Code."
    $manualNotes += "2. Verify formatter and HDL-related extensions first."
    $manualNotes += "3. Only handle VSIX/manual extensions if you still need them."
    $manualNotes += ""
    $manualNotes += "## VSIX Or Manual Extensions"
    $manualNotes += ""
    if ($manualExtensions.Count -eq 0) {
        $manualNotes += "- None"
    } else {
        foreach ($record in $manualExtensions) {
            $manualNotes += "- $($record.Id) | source=$($record.SourceType) | relativeLocation=$($record.RelativeLocation)"
        }
    }
    $manualExtensionNotesPath = Join-Path $runDir "Manual_VSIX_Extensions.md"
    Write-Utf8File -Path $manualExtensionNotesPath -Content ($manualNotes -join "`r`n")
}

$settingsReport = @()
$settingsReport += "# Settings Migration Report"
$settingsReport += ""
$settingsReport += "## Staged Output"
$settingsReport += ""
$settingsReport += "- Staged settings path: $stagedSettingsDst"
$settingsReport += "- Removed Antigravity-only keys: $(@($stagedSettingsLog.RemovedKeys).Count)"
foreach ($entry in $stagedSettingsLog.RemovedKeys) {
    $settingsReport += "- Removed: $entry"
}
foreach ($entry in $stagedSettingsLog.UpdatedItems) {
    $settingsReport += "- Updated: $entry"
}
foreach ($entry in $stagedSettingsLog.Warnings) {
    $settingsReport += "- Warning: $entry"
}
if ($ApplyConfig) {
    $settingsReport += ""
    $settingsReport += "## Applied Output"
    $settingsReport += ""
    $settingsReport += "- Target user dir: $resolvedTargetUserDir"
    foreach ($entry in $applyLog) {
        $settingsReport += "- $($entry.Item): $($entry.Copied)"
    }
}
$settingsReportPath = Join-Path $runDir "Settings_Migration_Report.md"
Write-Utf8File -Path $settingsReportPath -Content ($settingsReport -join "`r`n")

$extensionReport = @()
$extensionReport += "# Extension Migration Report"
$extensionReport += ""
$extensionReport += "## Inventory"
$extensionReport += ""
$extensionReport += "- Total Antigravity extensions: $($extensionRecords.Count)"
$extensionReport += "- Gallery-backed extensions: $($galleryExtensions.Count)"
$extensionReport += "- Manual or VSIX-backed extensions: $($manualExtensions.Count)"
$extensionReport += "- Skipped product-specific extensions: $($skipExtensions.Count)"
$extensionReport += "- Manual install checklist: $manualExtensionListPath"
$extensionReport += ""
$extensionReport += "## Staged Copy Result"
$extensionReport += ""
if ($IncludeExtensionArtifacts) {
    foreach ($entry in $stagedExtensionLog) {
        $extensionReport += "- $($entry.Id) | source=$($entry.SourceType) | copied=$($entry.Copied) | skipped=$($entry.Skipped) | reason=$($entry.Reason)"
    }
} else {
    $extensionReport += "- No extension folders were copied in this run."
    $extensionReport += "- This lightweight mode assumes you will install extensions manually."
}
if ($GenerateExtensionInstallScript) {
    $extensionReport += ""
    $extensionReport += "## Generated Helper Scripts"
    $extensionReport += ""
    $extensionReport += "- Gallery install script: $galleryInstallScriptPath"
    $extensionReport += "- Manual VSIX notes: $manualExtensionNotesPath"
}
if ($InstallExtensions) {
    $extensionReport += ""
    $extensionReport += "## Immediate Install Results"
    $extensionReport += ""
    foreach ($entry in $extensionInstallResults) {
        $extensionReport += "- $($entry.Id): $($entry.Success)"
    }
}
$extensionReportPath = Join-Path $runDir "Extension_Migration_Report.md"
Write-Utf8File -Path $extensionReportPath -Content ($extensionReport -join "`r`n")

$summary = @()
$summary += "# Migration Summary"
$summary += ""
$summary += "## Mode"
$summary += ""
$summary += "- ApplyConfig: $ApplyConfig"
$summary += "- GenerateExtensionInstallScript: $GenerateExtensionInstallScript"
$summary += "- InstallExtensions: $InstallExtensions"
$summary += "- IncludeExtensionArtifacts: $IncludeExtensionArtifacts"
$summary += "- SkipBackups: $SkipBackups"
$summary += "- ProfileName (staging label): $ProfileName"
$summary += "- RunDir: $runDir"
$summary += "- StagedUserDataDir: $stagedUserDataDir"
$summary += "- StagedExtensionsDir: $(if ($IncludeExtensionArtifacts) { $stagedExtensionsDir } else { 'not-created' })"
$summary += "- PreviewScript: $previewScriptPath"
$summary += ""
$summary += "## Backups"
$summary += ""
if ($SkipBackups) {
    $summary += "- Backups were skipped by request."
} else {
    $summary += "- BackupDir: $backupDir"
    foreach ($entry in $backupLog) {
        $summary += "- $($entry.Label): copied=$($entry.Copied)"
    }
    if (-not $IncludeExtensionArtifacts) {
        $summary += "- Lightweight backup mode was used: extension folders were not backed up."
    }
}
$summary += ""
$summary += "## Staged Config"
$summary += ""
foreach ($entry in $stagedConfigLog) {
    $summary += "- $($entry.Item): copied=$($entry.Copied) -> $($entry.Target)"
}
$summary += ""
$summary += "## Staged Settings Review"
$summary += ""
if ($stagedSettingsLog.RemovedKeys.Count -eq 0 -and $stagedSettingsLog.UpdatedItems.Count -eq 0 -and $stagedSettingsLog.Warnings.Count -eq 0) {
    $summary += "- No special cleanup actions were needed."
} else {
    foreach ($entry in $stagedSettingsLog.RemovedKeys) {
        $summary += "- Removed key: $entry"
    }
    foreach ($entry in $stagedSettingsLog.UpdatedItems) {
        $summary += "- Updated item: $entry"
    }
    foreach ($entry in $stagedSettingsLog.Warnings) {
        $summary += "- Warning: $entry"
    }
}
$summary += ""
$summary += "## Extension Handling"
$summary += ""
$summary += "- Staged extension folders copied: $(if ($IncludeExtensionArtifacts) { @($stagedExtensionLog | Where-Object { $_.Copied }).Count } else { 0 })"
$summary += "- Gallery install candidates: $($galleryExtensions.Count)"
$summary += "- Manual fallback candidates: $($manualExtensions.Count)"
$summary += "- Manual install checklist: $manualExtensionListPath"
if ($GenerateExtensionInstallScript) {
    $summary += "- Gallery install script: $galleryInstallScriptPath"
    $summary += "- Manual VSIX notes: $manualExtensionNotesPath"
}
if ($InstallExtensions) {
    $summary += "- Immediate install successes: $(@($extensionInstallResults | Where-Object { $_.Success }).Count)"
    $summary += "- Immediate install failures: $(@($extensionInstallResults | Where-Object { -not $_.Success }).Count)"
}
$summary += ""
$summary += "## Real Apply"
$summary += ""
if ($ApplyConfig) {
    $summary += "- TargetUserDir: $resolvedTargetUserDir"
    foreach ($entry in $applyLog) {
        $summary += "- $($entry.Item): copied=$($entry.Copied)"
    }
} else {
    $summary += "- No real VS Code user directory was modified in this run."
    $summary += "- Re-run with -ApplyConfig to write the sanitized config into a real target user directory."
    $summary += "- If you want a named VS Code profile, create it first, find its actual profile User directory, and pass it through -TargetUserDir."
}
$summary += ""
$summary += "## Suggested Next Actions"
$summary += ""
$summary += "- Review Settings_Migration_Report.md for warnings."
$summary += "- Run preview_staged_vscode.ps1 to inspect the isolated preview environment."
$summary += "- If the preview is acceptable, re-run this script with -ApplyConfig."
$summary += "- Use VSCode_Extensions_Manual_Install.md as the manual plugin checklist."
if ($GenerateExtensionInstallScript) {
    $summary += "- If you later want batch installation, use install_gallery_extensions.ps1."
}
$summaryPath = Join-Path $runDir "Migration_Summary.md"
Write-Utf8File -Path $summaryPath -Content ($summary -join "`r`n")

$walkthrough = @()
$walkthrough += "# Walkthrough"
$walkthrough += ""
$walkthrough += "## What this run generated"
$walkthrough += ""
$walkthrough += "- A staged VS Code user-data directory for preview."
$walkthrough += "- A manual extension checklist."
$walkthrough += "- A preview launcher script."
$walkthrough += "- A migration summary and focused settings/extension reports."
if ($GenerateExtensionInstallScript) {
    $walkthrough += "- A gallery install script and a VSIX/manual extension note file."
}
if ($IncludeExtensionArtifacts) {
    $walkthrough += "- A staged extension directory copied from Antigravity."
}
$walkthrough += ""
$walkthrough += "## Suggested usage"
$walkthrough += ""
$walkthrough += "1. Run this script once without -ApplyConfig."
$walkthrough += "2. Read Migration_Summary.md and Settings_Migration_Report.md."
$walkthrough += "3. Read VSCode_Extensions_Manual_Install.md and install the plugins you actually want by hand."
$walkthrough += "4. Run preview_staged_vscode.ps1 and open one of your FPGA projects in the staged environment."
$walkthrough += "5. Confirm formatter, snippets, terminal, language pack, and AI workflow behavior."
$walkthrough += "6. Re-run with -ApplyConfig only after the staged preview looks correct."
if ($GenerateExtensionInstallScript) {
    $walkthrough += "7. If you later want batch installation, use install_gallery_extensions.ps1."
}
$walkthroughPath = Join-Path $runDir "Walkthrough.md"
Write-Utf8File -Path $walkthroughPath -Content ($walkthrough -join "`r`n")

Write-Host "Migration package generated at: $runDir"
Write-Host "Summary file: $summaryPath"
