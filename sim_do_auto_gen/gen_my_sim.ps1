param(
  [Alias("QuestaDir")][string]$SimulatorDir = "",
  [string]$OutTclName = "my_sim.tcl",
  [string]$OutBatName = "my_sim.bat",
  [switch]$NoUi
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$script:ProjectLeafSearchCache = @{}
$script:CommonResourceFolderNames = @("mem", "rom", "data", "init", "coef", "coeff", "table", "tables", "lut", "rtl")

function Write-Utf8NoBomFile {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][AllowEmptyString()][string[]]$Lines
  )

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $text = (($Lines -join "`r`n").TrimEnd("`r", "`n")) + "`r`n"
  [System.IO.File]::WriteAllText($Path, $text, $utf8NoBom)
}

function Read-Utf8TextFile {
  param([Parameter(Mandatory = $true)][string]$Path)

  $reader = New-Object System.IO.StreamReader($Path, $true)
  try {
    return $reader.ReadToEnd()
  }
  finally {
    $reader.Dispose()
  }
}

function Read-Utf8Lines {
  param([Parameter(Mandatory = $true)][string]$Path)

  $text = Read-Utf8TextFile -Path $Path
  if ([string]::IsNullOrEmpty($text)) {
    return @()
  }

  $lines = [System.Text.RegularExpressions.Regex]::Split($text, "\r\n|\n")
  if ($lines.Count -gt 0 -and $lines[$lines.Count - 1] -eq "") {
    return $lines[0..($lines.Count - 2)]
  }

  return $lines
}

function Write-GenerationLog {
  param(
    [Parameter(Mandatory = $true)][string]$Message,
    [object]$LogBox = $null
  )

  $entry = "[{0}] {1}" -f (Get-Date).ToString("HH:mm:ss"), $Message
  Write-Host $entry

  if ($null -eq $LogBox) {
    return
  }

  $appendAction = {
    param($TargetBox, $TargetEntry)

    if ([string]::IsNullOrWhiteSpace($TargetBox.Text)) {
      $TargetBox.Text = $TargetEntry
    }
    else {
      $TargetBox.AppendText([Environment]::NewLine + $TargetEntry)
    }
    $TargetBox.SelectionStart = $TargetBox.TextLength
    $TargetBox.ScrollToCaret()
  }

  if ($LogBox.InvokeRequired) {
    $LogBox.Invoke($appendAction, $LogBox, $entry) | Out-Null
  }
  else {
    & $appendAction $LogBox $entry
  }
}

function Resolve-ExistingWaveBlock {
  param([string]$MySimTclPath)

  $defaultBlock = @(
    "#user wave-watch add here",
    "# add wave -position insertpoint sim:/<tb>/<path>/*",
    "#user wave-watch add here end"
  )

  if (-not (Test-Path -LiteralPath $MySimTclPath)) {
    return $defaultBlock
  }

  $lines = Read-Utf8Lines -Path $MySimTclPath
  $start = -1
  $end = -1

  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($start -lt 0 -and $lines[$i] -match "^\s*#user wave-watch add here\s*$") {
      $start = $i
      continue
    }

    if ($start -ge 0 -and $lines[$i] -match "^\s*#user wave-watch add here end\s*$") {
      $end = $i
      break
    }
  }

  if ($start -ge 0 -and $end -ge $start) {
    return $lines[$start..$end]
  }

  return $defaultBlock
}

function Resolve-WaveBlockWithFallback {
  param(
    [Parameter(Mandatory = $true)][string]$PrimaryTclPath,
    [string[]]$FallbackTclPaths = @()
  )

  $primaryBlock = Resolve-ExistingWaveBlock -MySimTclPath $PrimaryTclPath
  $defaultBlock = @(
    "#user wave-watch add here",
    "# add wave -position insertpoint sim:/<tb>/<path>/*",
    "#user wave-watch add here end"
  )

  if (($primaryBlock -join "`n") -ne ($defaultBlock -join "`n")) {
    return $primaryBlock
  }

  foreach ($fallbackPath in $FallbackTclPaths) {
    if ([string]::IsNullOrWhiteSpace($fallbackPath)) {
      continue
    }

    if (-not (Test-Path -LiteralPath $fallbackPath)) {
      continue
    }

    $fallbackBlock = Resolve-ExistingWaveBlock -MySimTclPath $fallbackPath
    if (($fallbackBlock -join "`n") -ne ($defaultBlock -join "`n")) {
      return $fallbackBlock
    }
  }

  return $primaryBlock
}

function Resolve-ExistingRunLine {
  param([string]$MySimTclPath)

  $defaultRun = "run 100ms"
  if (-not (Test-Path -LiteralPath $MySimTclPath)) {
    return $defaultRun
  }

  $line = Read-Utf8Lines -Path $MySimTclPath | Where-Object { $_ -match "^\s*run\s+\S+" } | Select-Object -Last 1
  if ([string]::IsNullOrWhiteSpace($line)) {
    return $defaultRun
  }

  return $line.Trim()
}

function Get-SimulatorContext {
  param([Parameter(Mandatory = $true)][string]$SimulatorDir)

  if ([string]::IsNullOrWhiteSpace($SimulatorDir)) {
    throw "请选择有效的 questa/modelsim 目录。"
  }

  if (-not (Test-Path -LiteralPath $SimulatorDir)) {
    throw "目录不存在: $SimulatorDir"
  }

  $resolvedDir = (Resolve-Path -LiteralPath $SimulatorDir).Path
  $compileCandidates = @(
    Get-ChildItem -LiteralPath $resolvedDir -File -Filter "*_compile.do" |
      Sort-Object LastWriteTime -Descending
  )

  if ($compileCandidates.Count -eq 0) {
    throw "目标目录中未找到 '*_compile.do'：$resolvedDir"
  }

  $compileDo = $compileCandidates[0]
  $baseName = $compileDo.BaseName -replace "_compile$", ""
  $elaborateDo = Join-Path $resolvedDir ($baseName + "_elaborate.do")
  $simulateDo = Join-Path $resolvedDir ($baseName + "_simulate.do")
  $simulateBat = Join-Path $resolvedDir "simulate.bat"

  foreach ($requiredPath in @($elaborateDo, $simulateDo, $simulateBat)) {
    if (-not (Test-Path -LiteralPath $requiredPath)) {
      throw "缺少必须文件: $requiredPath"
    }
  }

  $outputDir = Split-Path -Parent $resolvedDir
  $simLeafName = Split-Path -Leaf $resolvedDir

  return [pscustomobject]@{
    SimulatorDir    = $resolvedDir
    SimulatorLeaf   = $simLeafName
    OutputDir       = $outputDir
    CompileDo       = $compileDo.FullName
    CompileDoName   = $compileDo.Name
    ElaborateDo     = $elaborateDo
    ElaborateDoName = [System.IO.Path]::GetFileName($elaborateDo)
    SimulateDo      = $simulateDo
    SimulateDoName  = [System.IO.Path]::GetFileName($simulateDo)
    SimulateBat     = $simulateBat
  }
}

function Get-FilteredCompileLines {
  param([Parameter(Mandatory = $true)][string]$Path)

  return @(
    Read-Utf8Lines -Path $Path |
      Where-Object { $_ -notmatch "^\s*quit\s+-force(?:\s+-code\s+\d+)?\s*$" }
  )
}

function Get-FilteredElaborateLines {
  param([Parameter(Mandatory = $true)][string]$Path)

  return @(
    Read-Utf8Lines -Path $Path |
      Where-Object {
        $_ -notmatch "^\s*$" -and
        $_ -notmatch "^\s*#" -and
        $_ -notmatch "^\s*quit\s+-force(?:\s+-code\s+\d+)?\s*$"
      }
  )
}

function Get-FilteredSimulateLines {
  param([Parameter(Mandatory = $true)][string]$Path)

  $filteredLines = New-Object System.Collections.Generic.List[string]
  foreach ($line in (Read-Utf8Lines -Path $Path)) {
    if ($line -match "^\s*$") { continue }
    if ($line -match "^\s*#") { continue }
    if ($line -match "^\s*quit\s+-force(?:\s+-code\s+\d+)?\s*$") { continue }
    if ($line -match "^\s*do\s+(\{.*_wave\.do\}|\"".*_wave\.do\""|[^ ]*_wave\.do)\s*$") { continue }
    if ($line -match "^\s*do\s+(\{.*\.udo\}|\"".*\.udo\""|[^ ]*\.udo)\s*$") { continue }
    if ($line -match "^\s*run\s+\S+") { continue }
    if ($line -match "^\s*view\s+\S+") { continue }
    $filteredLines.Add($line)
  }

  return $filteredLines.ToArray()
}

function Resolve-BinPathFromSimulateBat {
  param([Parameter(Mandatory = $true)][string]$SimulateBatPath)

  $binLine = Read-Utf8Lines -Path $SimulateBatPath |
    Where-Object { $_ -match "^\s*set\s+bin_path\s*=" } |
    Select-Object -First 1

  if ([string]::IsNullOrWhiteSpace($binLine)) {
    return ""
  }

  if ($binLine -match "^\s*set\s+bin_path\s*=\s*(.+?)\s*$") {
    return $matches[1].Trim().Trim('"')
  }

  return ""
}

function Convert-ToTclPath {
  param([Parameter(Mandatory = $true)][string]$Path)

  return $Path.Replace("\", "/")
}

function Get-NormalizedPathText {
  param([Parameter(Mandatory = $true)][string]$Path)

  return $Path.Replace("/", "\").TrimEnd("\").ToLowerInvariant()
}

function Get-PathSegments {
  param([Parameter(Mandatory = $true)][string]$Path)

  return @(
    (Get-NormalizedPathText -Path $Path) -split "\\+" |
      Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
  )
}

function Get-CommonPathSegmentCount {
  param(
    [Parameter(Mandatory = $true)][string]$LeftPath,
    [Parameter(Mandatory = $true)][string]$RightPath
  )

  $leftSegments = @(Get-PathSegments -Path $LeftPath)
  $rightSegments = @(Get-PathSegments -Path $RightPath)
  $commonCount = [Math]::Min($leftSegments.Count, $rightSegments.Count)

  for ($i = 0; $i -lt $commonCount; $i++) {
    if ($leftSegments[$i] -ne $rightSegments[$i]) {
      return $i
    }
  }

  return $commonCount
}

function Test-IsPathUnder {
  param(
    [Parameter(Mandatory = $true)][string]$ChildPath,
    [Parameter(Mandatory = $true)][string]$ParentPath
  )

  $childText = (Get-NormalizedPathText -Path $ChildPath) + "\"
  $parentText = (Get-NormalizedPathText -Path $ParentPath) + "\"
  return $childText.StartsWith($parentText, [System.StringComparison]::OrdinalIgnoreCase)
}

function Add-UniqueString {
  param(
    [Parameter(Mandatory = $true)]$List,
    [Parameter(Mandatory = $true)][string]$Value
  )

  if ([string]::IsNullOrWhiteSpace($Value)) {
    return
  }

  if (-not $List.Contains($Value)) {
    $List.Add($Value) | Out-Null
  }
}

function Get-ProjectSearchRoot {
  param([Parameter(Mandatory = $true)][string]$SimulatorDir)

  $currentDir = Get-Item -LiteralPath (Resolve-Path -LiteralPath $SimulatorDir).Path
  while ($null -ne $currentDir) {
    if ($currentDir.Name -match "\.(sim|srcs)$") {
      return $currentDir.Parent.FullName
    }

    $xprFiles = @(
      Get-ChildItem -LiteralPath $currentDir.FullName -File -Filter "*.xpr" -ErrorAction SilentlyContinue
    )
    if ($xprFiles.Count -gt 0) {
      return $currentDir.FullName
    }

    $currentDir = $currentDir.Parent
  }

  return (Split-Path -Parent (Resolve-Path -LiteralPath $SimulatorDir).Path)
}

function Get-ProjectLeafSearchCandidates {
  param(
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [Parameter(Mandatory = $true)][string]$LeafName
  )

  $resolvedRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
  $cacheKey = "{0}|{1}" -f (Get-NormalizedPathText -Path $resolvedRoot), $LeafName.ToLowerInvariant()
  if ($script:ProjectLeafSearchCache.ContainsKey($cacheKey)) {
    return $script:ProjectLeafSearchCache[$cacheKey]
  }

  $matches = @(
    Get-ChildItem -LiteralPath $resolvedRoot -Recurse -File -Filter $LeafName -ErrorAction SilentlyContinue |
      ForEach-Object { $_.FullName } |
      Select-Object -Unique
  )
  $script:ProjectLeafSearchCache[$cacheKey] = $matches
  return $matches
}

function Get-CompileSourceFilesFromLines {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][AllowEmptyString()][string[]]$CompileLines,
    [Parameter(Mandatory = $true)][string]$SimulatorDir
  )

  $resolvedFiles = New-Object System.Collections.Generic.List[string]

  foreach ($line in $CompileLines) {
    foreach ($match in [System.Text.RegularExpressions.Regex]::Matches($line, '"([^"]+)"')) {
      $candidate = $match.Groups[1].Value
      if ([string]::IsNullOrWhiteSpace($candidate)) {
        continue
      }

      if ($candidate -eq "glbl.v") {
        continue
      }

      $fullPath = if ([System.IO.Path]::IsPathRooted($candidate)) {
        $candidate
      }
      else {
        Join-Path $SimulatorDir $candidate
      }

      if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        continue
      }

      Add-UniqueString -List $resolvedFiles -Value ((Resolve-Path -LiteralPath $fullPath).Path)
    }
  }

  return $resolvedFiles.ToArray()
}

function Get-MemoryReferenceCandidatePaths {
  param(
    [Parameter(Mandatory = $true)][string]$SourceFile,
    [Parameter(Mandatory = $true)][string]$MemRef,
    [Parameter(Mandatory = $true)][string]$ProjectRoot
  )

  $candidatePaths = New-Object System.Collections.Generic.List[string]
  $sourceDir = Split-Path -Parent $SourceFile

  if ([System.IO.Path]::IsPathRooted($MemRef)) {
    if (Test-Path -LiteralPath $MemRef -PathType Leaf) {
      Add-UniqueString -List $candidatePaths -Value ((Resolve-Path -LiteralPath $MemRef).Path)
    }
    return $candidatePaths.ToArray()
  }

  $searchBases = New-Object System.Collections.Generic.List[string]
  $currentDir = $sourceDir
  $walkDepth = 0

  while (-not [string]::IsNullOrWhiteSpace($currentDir)) {
    Add-UniqueString -List $searchBases -Value $currentDir
    foreach ($folderName in $script:CommonResourceFolderNames) {
      $resourceDir = Join-Path $currentDir $folderName
      if (Test-Path -LiteralPath $resourceDir -PathType Container) {
        Add-UniqueString -List $searchBases -Value $resourceDir
      }
    }

    if ((Get-NormalizedPathText -Path $currentDir) -eq (Get-NormalizedPathText -Path $ProjectRoot)) {
      break
    }

    if ($walkDepth -ge 4) {
      break
    }

    $parentDir = Split-Path -Parent $currentDir
    if ([string]::IsNullOrWhiteSpace($parentDir) -or ((Get-NormalizedPathText -Path $parentDir) -eq (Get-NormalizedPathText -Path $currentDir))) {
      break
    }

    $currentDir = $parentDir
    $walkDepth++
  }

  foreach ($baseDir in $searchBases) {
    $candidate = Join-Path $baseDir $MemRef
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
      Add-UniqueString -List $candidatePaths -Value ((Resolve-Path -LiteralPath $candidate).Path)
    }
  }

  $leafName = [System.IO.Path]::GetFileName($MemRef)
  if (-not [string]::IsNullOrWhiteSpace($leafName)) {
    foreach ($projectCandidate in @(Get-ProjectLeafSearchCandidates -ProjectRoot $ProjectRoot -LeafName $leafName)) {
      Add-UniqueString -List $candidatePaths -Value $projectCandidate
    }
  }

  return $candidatePaths.ToArray()
}

function Get-MemoryReferenceCandidateScore {
  param(
    [Parameter(Mandatory = $true)][string]$SourceFile,
    [Parameter(Mandatory = $true)][string]$MemRef,
    [Parameter(Mandatory = $true)][string]$CandidatePath
  )

  $sourceDir = Split-Path -Parent $SourceFile
  $candidateDir = Split-Path -Parent $CandidatePath
  $score = 0

  if ((Get-NormalizedPathText -Path $candidateDir) -eq (Get-NormalizedPathText -Path $sourceDir)) {
    $score += 10000
  }

  if (Test-IsPathUnder -ChildPath $CandidatePath -ParentPath $sourceDir) {
    $score += 2000
  }

  $memRefNorm = (Get-NormalizedPathText -Path $MemRef)
  $candidateNorm = (Get-NormalizedPathText -Path $CandidatePath)
  if ($memRefNorm.Contains("\") -and $candidateNorm.EndsWith("\" + $memRefNorm, [System.StringComparison]::OrdinalIgnoreCase)) {
    $score += 1500
  }

  $commonCount = Get-CommonPathSegmentCount -LeftPath $sourceDir -RightPath $candidateDir
  $sourceSegments = Get-PathSegments -Path $sourceDir
  $candidateSegments = Get-PathSegments -Path $candidateDir
  $distance = ($sourceSegments.Count - $commonCount) + ($candidateSegments.Count - $commonCount)
  $score += ($commonCount * 100) - $distance

  $candidateLeafDir = [System.IO.Path]::GetFileName($candidateDir)
  if ($script:CommonResourceFolderNames -contains $candidateLeafDir.ToLowerInvariant()) {
    $score += 25
  }

  return $score
}

function Resolve-MemoryReferenceSource {
  param(
    [Parameter(Mandatory = $true)][string]$SourceFile,
    [Parameter(Mandatory = $true)][string]$MemRef,
    [Parameter(Mandatory = $true)][string]$ProjectRoot,
    [scriptblock]$CandidateSelectionCallback = $null,
    [object]$LogBox = $null
  )

  $candidatePaths = @(Get-MemoryReferenceCandidatePaths -SourceFile $SourceFile -MemRef $MemRef -ProjectRoot $ProjectRoot)
  if ($candidatePaths.Count -eq 0) {
    Write-GenerationLog -Message ("未解析到初始化文件 / Memory init file unresolved: {0} (source: {1})" -f $MemRef, $SourceFile) -LogBox $LogBox
    return ""
  }

  if ($candidatePaths.Count -eq 1) {
    return $candidatePaths[0]
  }

  $scoredCandidates = @(
    $candidatePaths |
      ForEach-Object {
        [pscustomobject]@{
          Path  = $_
          Score = Get-MemoryReferenceCandidateScore -SourceFile $SourceFile -MemRef $MemRef -CandidatePath $_
        }
      } |
      Sort-Object -Property @(
        @{ Expression = "Score"; Descending = $true },
        @{ Expression = "Path"; Descending = $false }
      )
  )

  $recommendedPath = $scoredCandidates[0].Path
  Write-GenerationLog -Message ("检测到多个初始化文件候选 / Multiple memory init candidates detected: {0}" -f $MemRef) -LogBox $LogBox
  Write-GenerationLog -Message ("工具推荐候选 / Recommended candidate: {0}" -f $recommendedPath) -LogBox $LogBox

  if ($null -ne $CandidateSelectionCallback) {
    $selectedPath = & $CandidateSelectionCallback ([pscustomobject]@{
      SourceFile      = $SourceFile
      MemoryReference = $MemRef
      RecommendedPath = $recommendedPath
      Candidates      = $scoredCandidates
    })

    if (-not [string]::IsNullOrWhiteSpace($selectedPath) -and ($candidatePaths -contains $selectedPath)) {
      Write-GenerationLog -Message ("已选择候选 / Selected candidate: {0}" -f $selectedPath) -LogBox $LogBox
      return $selectedPath
    }
  }

  Write-GenerationLog -Message ("未显式选择候选，采用推荐项 / No explicit selection provided, use recommended candidate: {0}" -f $recommendedPath) -LogBox $LogBox
  return $recommendedPath
}

function Get-MemoryInitSyncItems {
  param(
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][AllowEmptyString()][string[]]$CompileLines,
    [Parameter(Mandatory = $true)][string]$SimulatorDir,
    [scriptblock]$CandidateSelectionCallback = $null,
    [object]$LogBox = $null
  )

  $syncItems = New-Object System.Collections.Generic.List[object]
  $compileSources = @(Get-CompileSourceFilesFromLines -CompileLines $CompileLines -SimulatorDir $SimulatorDir)
  $projectRoot = Get-ProjectSearchRoot -SimulatorDir $SimulatorDir
  Write-GenerationLog -Message ("初始化文件搜索根目录 / Memory init search root: {0}" -f $projectRoot) -LogBox $LogBox

  foreach ($sourceFile in $compileSources) {
    foreach ($line in (Read-Utf8Lines -Path $sourceFile)) {
      foreach ($match in [System.Text.RegularExpressions.Regex]::Matches($line, '\$readmem(?:b|h)\s*\(\s*"([^"]+)"')) {
        $memRef = $match.Groups[1].Value
        if ([string]::IsNullOrWhiteSpace($memRef)) {
          continue
        }

        $memSource = Resolve-MemoryReferenceSource -SourceFile $sourceFile -MemRef $memRef -ProjectRoot $projectRoot -CandidateSelectionCallback $CandidateSelectionCallback -LogBox $LogBox
        if ([string]::IsNullOrWhiteSpace($memSource)) {
          continue
        }

        $targetPath = if ([System.IO.Path]::IsPathRooted($memRef)) {
          Join-Path $SimulatorDir ([System.IO.Path]::GetFileName($memRef))
        }
        else {
          Join-Path $SimulatorDir $memRef
        }

        $syncItems.Add([pscustomobject]@{
          Source = $memSource
          Target = $targetPath
        })
      }
    }
  }

  return @(
    $syncItems |
      Group-Object Target |
      ForEach-Object { $_.Group[0] }
  )
}

function Generate-MySimArtifacts {
  param(
    [Parameter(Mandatory = $true)][string]$SimulatorDir,
    [Parameter(Mandatory = $true)][string]$OutTclName,
    [Parameter(Mandatory = $true)][string]$OutBatName,
    [object]$LogBox = $null,
    [scriptblock]$CandidateSelectionCallback = $null
  )

  Write-GenerationLog -Message "开始处理目录 / Start processing: $SimulatorDir" -LogBox $LogBox
  $context = Get-SimulatorContext -SimulatorDir $SimulatorDir
  Write-GenerationLog -Message "已确认源目录 / Source directory confirmed: $($context.SimulatorDir)" -LogBox $LogBox
  Write-GenerationLog -Message "输出文件将写入上一级目录 / Output parent directory: $($context.OutputDir)" -LogBox $LogBox

  $outTclPath = Join-Path $context.OutputDir $OutTclName
  $outBatPath = Join-Path $context.OutputDir $OutBatName
  $legacyTclPath = Join-Path $context.SimulatorDir $OutTclName

  $waveBlock = Resolve-WaveBlockWithFallback -PrimaryTclPath $outTclPath -FallbackTclPaths @($legacyTclPath)
  $runLine = Resolve-ExistingRunLine -MySimTclPath $outTclPath
  Write-GenerationLog -Message "已读取保留区 / Preserved user block and run line have been loaded." -LogBox $LogBox
  if ((Test-Path -LiteralPath $legacyTclPath) -and -not (Test-Path -LiteralPath $outTclPath)) {
    Write-GenerationLog -Message "检测到目标目录中的旧版 TCL，已尝试继承用户波形块 / Legacy TCL in simulator directory detected, wave block fallback applied." -LogBox $LogBox
  }

  $compileLines = Get-FilteredCompileLines -Path $context.CompileDo
  $elaborateLines = Get-FilteredElaborateLines -Path $context.ElaborateDo
  $simulateLines = Get-FilteredSimulateLines -Path $context.SimulateDo
  $binPath = Resolve-BinPathFromSimulateBat -SimulateBatPath $context.SimulateBat
  $memInitSyncItems = @(Get-MemoryInitSyncItems -CompileLines $compileLines -SimulatorDir $context.SimulatorDir -CandidateSelectionCallback $CandidateSelectionCallback -LogBox $LogBox)

  $created = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
  $outTclLines = @(
    "######################################################################",
    "# EN: File name : $OutTclName",
    "# CN: 文件名 : $OutTclName",
    "# EN: Created on: $created",
    "# CN: 生成时间 : $created",
    "# EN: Source directory : $($context.SimulatorDir)",
    "# CN: 来源目录 : $($context.SimulatorDir)",
    "# EN: This TCL wrapper must stay in the parent directory of '$($context.SimulatorLeaf)'.",
    "# CN: 本 TCL 包装脚本必须放在 '$($context.SimulatorLeaf)' 的上一级目录。",
    "######################################################################",
    "",
    "# EN: Exit with a non-zero code on script errors. / 脚本报错时返回非零退出码。",
    "onerror {quit -code 1}",
    "transcript on",
    "",
    "# EN: Resolve the parent/output directory and the actual simulator directory. / 解析上一级输出目录和实际仿真器目录。",
    "# EN: Use the current working directory set by my_sim.bat instead of relying on 'info script'. / 使用 my_sim.bat 设定的当前目录，而不是依赖 'info script'。",
    "set launch_dir [file normalize [pwd]]",
    "set sim_subdir {$($context.SimulatorLeaf)}",
    "set sim_dir [file normalize [file join `$launch_dir `$sim_subdir]]",
    "puts `"INFO: launch directory      = `$launch_dir`"",
    "puts `"INFO: simulator script folder = `$sim_dir`"",
    "if {![file isdirectory `$sim_dir]} {",
    "  puts stderr `"ERROR: simulator script directory does not exist: `$sim_dir`"",
    "  puts stderr `"ERROR: run $OutBatName from the parent directory of $($context.SimulatorLeaf).`"",
    "  quit -code 1",
    "}",
    "if {[catch {cd `$sim_dir} cdError]} {",
    "  puts stderr `"ERROR: failed to switch to simulator directory: `$sim_dir`"",
    "  puts stderr `$cdError",
    "  quit -code 1",
    "}",
    "puts `"INFO: working directory switched to `$sim_dir`"",
    "",
    "######################################################################",
    "# EN: Section A - Compile and library setup.",
    "# CN: 段A - 编译与库映射配置。",
    "# EN: Relative paths must execute inside '$($context.SimulatorLeaf)'.",
    "# CN: 相对路径必须在 '$($context.SimulatorLeaf)' 目录内执行。",
    "######################################################################",
    "puts `"INFO: section A start / compile and library setup`"",
    ""
  )

  if ($memInitSyncItems.Count -gt 0) {
    $outTclLines += @(
      "######################################################################",
      "# EN: Section A0 - Memory initialization file staging.",
      "# CN: 段A0 - 内存初始化文件同步。",
      "######################################################################",
      "puts `"INFO: section A0 start / sync memory init files`"",
      "set mem_init_sync_list [list \"
    )

    for ($i = 0; $i -lt $memInitSyncItems.Count; $i++) {
      $item = $memInitSyncItems[$i]
      $srcPath = Convert-ToTclPath -Path $item.Source
      $dstPath = Convert-ToTclPath -Path $item.Target
      $line = "  [list `"$srcPath`" `"$dstPath`"]"
      if ($i -lt ($memInitSyncItems.Count - 1)) {
        $line += " \"
      }
      $outTclLines += $line
    }

    $outTclLines += @(
      "]",
      "foreach mem_pair `$mem_init_sync_list {",
      "  set mem_src [lindex `$mem_pair 0]",
      "  set mem_dst [lindex `$mem_pair 1]",
      "  set mem_dst_dir [file dirname `$mem_dst]",
      "  if {![file exists `$mem_src]} {",
      "    puts stderr `"ERROR: memory init file not found: `$mem_src`"",
      "    quit -code 1",
      "  }",
      "  if {![file isdirectory `$mem_dst_dir]} {",
      "    file mkdir `$mem_dst_dir",
      "  }",
      "  if {[catch {file copy -force `$mem_src `$mem_dst} copyError]} {",
      "    puts stderr `"ERROR: failed to stage memory init file: `$mem_src -> `$mem_dst`"",
      "    puts stderr `$copyError",
      "    quit -code 1",
      "  }",
      "  puts `"INFO: staged memory init file: `$mem_src -> `$mem_dst`"",
      "}",
      ""
    )
  }

  $outTclLines += $compileLines
  $outTclLines += @(
    "",
    "######################################################################",
    "# EN: Section B - Elaborate commands.",
    "# CN: 段B - 设计展开命令。",
    "######################################################################",
    "puts `"INFO: section B start / elaborate`"",
    ""
  )

  $outTclLines += $elaborateLines
  $outTclLines += @(
    "",
    "######################################################################",
    "# EN: Section C - Core simulation startup commands.",
    "# CN: 段C - 仿真启动核心命令。",
    "# EN: Wave/view/run commands from Vivado are removed on purpose.",
    "# CN: Vivado 原始脚本中的 wave/view/run 命令已按设计去除。",
    "######################################################################",
    "puts `"INFO: section C start / simulation core`"",
    ""
  )

  $outTclLines += $simulateLines
  $outTclLines += @(
    "",
    "######################################################################",
    "# EN: Section D - User wave block.",
    "# CN: 段D - 用户波形配置块。",
    "######################################################################",
    "puts `"INFO: section D start / user wave block`"",
    ""
  )

  $outTclLines += $waveBlock
  $outTclLines += @(
    "",
    "######################################################################",
    "# EN: Section E - Viewer and runtime control.",
    "# CN: 段E - 波形窗口与运行时长控制。",
    "######################################################################",
    "puts `"INFO: section E start / viewer and runtime`"",
    "view wave",
    "view structure",
    "view signals",
    "",
    "#user decide sim time",
    $runLine,
    "",
    "puts `"INFO: runtime command finished or control returned to GUI shell.`""
  )

  Write-Utf8NoBomFile -Path $outTclPath -Lines $outTclLines
  Write-GenerationLog -Message "已生成 TCL 包装脚本 / Generated TCL wrapper: $outTclPath" -LogBox $LogBox

  $outBatLines = New-Object System.Collections.Generic.List[string]
  $outBatLines.Add("@echo off")
  $outBatLines.Add("setlocal")
  $outBatLines.Add("set ""SCRIPT_DIR=%~dp0""")
  $outBatLines.Add("pushd ""%SCRIPT_DIR%"" >nul")
  $outBatLines.Add("echo [INFO] Launcher directory  : %SCRIPT_DIR%")
  $outBatLines.Add("echo [INFO] Simulator subdir   : $($context.SimulatorLeaf)")
  $outBatLines.Add("echo [INFO] Generated TCL path : %SCRIPT_DIR%$OutTclName")
  $outBatLines.Add("echo [INFO] Keep this BAT and TCL in the parent directory of '$($context.SimulatorLeaf)'.")

  if ([string]::IsNullOrWhiteSpace($binPath)) {
    $outBatLines.Add("echo [INFO] bin_path not found in simulate.bat, fallback to vsim from PATH.")
    $outBatLines.Add("call vsim -do ""do {$OutTclName}"" -l simulate.log")
  }
  else {
    $outBatLines.Add("set ""bin_path=$binPath""")
    $outBatLines.Add("echo [INFO] Questa/ModelSim bin: %bin_path%")
    $outBatLines.Add("call ""%bin_path%\vsim"" -do ""do {$OutTclName}"" -l simulate.log")
  }

  $outBatLines.Add("set ""VSIM_EXIT=%ERRORLEVEL%""")
  $outBatLines.Add("popd >nul")
  $outBatLines.Add("if not ""%VSIM_EXIT%""==""0"" (")
  $outBatLines.Add("  echo [ERROR] Simulation launcher exited with code %VSIM_EXIT%.")
  $outBatLines.Add("  exit /b %VSIM_EXIT%")
  $outBatLines.Add(")")
  $outBatLines.Add("echo [INFO] Simulation launcher finished with code 0.")
  $outBatLines.Add("exit /b 0")

  Write-Utf8NoBomFile -Path $outBatPath -Lines $outBatLines.ToArray()
  Write-GenerationLog -Message "已生成 BAT 启动脚本 / Generated BAT launcher: $outBatPath" -LogBox $LogBox

  return [pscustomobject]@{
    SimulatorDir = $context.SimulatorDir
    OutputDir    = $context.OutputDir
    OutputTcl    = $outTclPath
    OutputBat    = $outBatPath
  }
}

function Show-GenerationCompletion {
  param(
    [Parameter(Mandatory = $true)]$Owner,
    [Parameter(Mandatory = $true)]$Result
  )

  $message = @"
已完成生成。

源目录：
$($Result.SimulatorDir)

输出目录（上一级）：
$($Result.OutputDir)

生成文件：
$($Result.OutputTcl)
$($Result.OutputBat)

请将生成出来的 BAT 和 TCL 保持放在上述上一级目录，
不要移动回 questa/modelsim 目录内，否则运行基准目录会失配。
"@

  [System.Windows.Forms.MessageBox]::Show(
    $Owner,
    $message,
    "生成完成 / Generation Completed",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
  ) | Out-Null
}

function Show-MemoryCandidateSelectionDialog {
  param(
    [Parameter(Mandatory = $true)]$Owner,
    [Parameter(Mandatory = $true)]$SelectionContext
  )

  $dialog = New-Object System.Windows.Forms.Form
  $dialog.Text = "选择初始化文件 / Select Memory Init File"
  $dialog.StartPosition = "CenterParent"
  $dialog.Size = New-Object System.Drawing.Size(980, 560)
  $dialog.MinimumSize = New-Object System.Drawing.Size(980, 560)
  $dialog.Font = New-Object System.Drawing.Font("Segoe UI", 10)
  $dialog.FormBorderStyle = "Sizable"
  $dialog.MaximizeBox = $false
  $dialog.MinimizeBox = $false

  $titleLabel = New-Object System.Windows.Forms.Label
  $titleLabel.Location = New-Object System.Drawing.Point(18, 18)
  $titleLabel.Size = New-Object System.Drawing.Size(924, 28)
  $titleLabel.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 12)
  $titleLabel.Text = "检测到多个初始化文件候选，请选择一个；默认已选中工具推荐项。"
  $dialog.Controls.Add($titleLabel)

  $refLabel = New-Object System.Windows.Forms.Label
  $refLabel.Location = New-Object System.Drawing.Point(18, 56)
  $refLabel.Size = New-Object System.Drawing.Size(924, 44)
  $refLabel.Text = "引用字符串 / Memory reference:`r`n$($SelectionContext.MemoryReference)"
  $dialog.Controls.Add($refLabel)

  $sourceLabel = New-Object System.Windows.Forms.Label
  $sourceLabel.Location = New-Object System.Drawing.Point(18, 108)
  $sourceLabel.Size = New-Object System.Drawing.Size(924, 44)
  $sourceLabel.Text = "来源源码 / Source file:`r`n$($SelectionContext.SourceFile)"
  $dialog.Controls.Add($sourceLabel)

  $recommendLabel = New-Object System.Windows.Forms.Label
  $recommendLabel.Location = New-Object System.Drawing.Point(18, 160)
  $recommendLabel.Size = New-Object System.Drawing.Size(924, 44)
  $recommendLabel.Text = "工具推荐 / Recommended:`r`n$($SelectionContext.RecommendedPath)"
  $dialog.Controls.Add($recommendLabel)

  $listLabel = New-Object System.Windows.Forms.Label
  $listLabel.Location = New-Object System.Drawing.Point(18, 214)
  $listLabel.Size = New-Object System.Drawing.Size(280, 24)
  $listLabel.Text = "候选列表 / Candidate list"
  $dialog.Controls.Add($listLabel)

  $candidateListBox = New-Object System.Windows.Forms.ListBox
  $candidateListBox.Location = New-Object System.Drawing.Point(18, 242)
  $candidateListBox.Size = New-Object System.Drawing.Size(924, 226)
  $candidateListBox.Anchor = "Top,Bottom,Left,Right"
  $candidateListBox.HorizontalScrollbar = $true
  $dialog.Controls.Add($candidateListBox)

  for ($i = 0; $i -lt $SelectionContext.Candidates.Count; $i++) {
    $candidate = $SelectionContext.Candidates[$i]
    [void]$candidateListBox.Items.Add($candidate.Path)
    if ($candidate.Path -eq $SelectionContext.RecommendedPath) {
      $candidateListBox.SelectedIndex = $i
    }
  }

  if ($candidateListBox.SelectedIndex -lt 0 -and $candidateListBox.Items.Count -gt 0) {
    $candidateListBox.SelectedIndex = 0
  }

  $detailLabel = New-Object System.Windows.Forms.Label
  $detailLabel.Location = New-Object System.Drawing.Point(18, 476)
  $detailLabel.Size = New-Object System.Drawing.Size(924, 24)
  $detailLabel.Anchor = "Bottom,Left,Right"
  $detailLabel.Text = "若直接关闭或取消，将继续使用默认推荐项。"
  $dialog.Controls.Add($detailLabel)

  $okButton = New-Object System.Windows.Forms.Button
  $okButton.Location = New-Object System.Drawing.Point(738, 504)
  $okButton.Size = New-Object System.Drawing.Size(96, 32)
  $okButton.Anchor = "Bottom,Right"
  $okButton.Text = "确定"
  $okButton.DialogResult = [System.Windows.Forms.DialogResult]::OK
  $dialog.Controls.Add($okButton)

  $cancelButton = New-Object System.Windows.Forms.Button
  $cancelButton.Location = New-Object System.Drawing.Point(846, 504)
  $cancelButton.Size = New-Object System.Drawing.Size(96, 32)
  $cancelButton.Anchor = "Bottom,Right"
  $cancelButton.Text = "取消"
  $cancelButton.DialogResult = [System.Windows.Forms.DialogResult]::Cancel
  $dialog.Controls.Add($cancelButton)

  $dialog.AcceptButton = $okButton
  $dialog.CancelButton = $cancelButton

  $result = $dialog.ShowDialog($Owner)
  if ($result -eq [System.Windows.Forms.DialogResult]::OK -and $candidateListBox.SelectedItem) {
    return [string]$candidateListBox.SelectedItem
  }

  return [string]$SelectionContext.RecommendedPath
}

function Show-GeneratorUi {
  param(
    [string]$InitialSimulatorDir = "",
    [string]$OutTclName = "my_sim.tcl",
    [string]$OutBatName = "my_sim.bat"
  )

  if ([System.Threading.Thread]::CurrentThread.ApartmentState -ne [System.Threading.ApartmentState]::STA) {
    throw "UI 模式需要 STA 线程。请优先通过 gen_my_sim.bat 启动。"
  }

  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing

  if ([string]::IsNullOrWhiteSpace($InitialSimulatorDir)) {
    $InitialSimulatorDir = (Resolve-Path -LiteralPath (Get-Location).Path).Path
  }

  $form = New-Object System.Windows.Forms.Form
  $form.Text = "Questa/ModelSim 脚本生成器"
  $form.StartPosition = "CenterScreen"
  $form.Size = New-Object System.Drawing.Size(900, 560)
  $form.MinimumSize = New-Object System.Drawing.Size(900, 560)
  $form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

  $titleLabel = New-Object System.Windows.Forms.Label
  $titleLabel.Location = New-Object System.Drawing.Point(18, 18)
  $titleLabel.Size = New-Object System.Drawing.Size(820, 28)
  $titleLabel.Font = New-Object System.Drawing.Font("Segoe UI Semibold", 13)
  $titleLabel.Text = "选择 Questa/ModelSim 目录并生成上一级运行脚本"
  $form.Controls.Add($titleLabel)

  $pathLabel = New-Object System.Windows.Forms.Label
  $pathLabel.Location = New-Object System.Drawing.Point(18, 62)
  $pathLabel.Size = New-Object System.Drawing.Size(220, 24)
  $pathLabel.Text = "目标目录"
  $form.Controls.Add($pathLabel)

  $pathTextBox = New-Object System.Windows.Forms.TextBox
  $pathTextBox.Location = New-Object System.Drawing.Point(18, 90)
  $pathTextBox.Size = New-Object System.Drawing.Size(730, 28)
  $pathTextBox.Anchor = "Top,Left,Right"
  $pathTextBox.Text = $InitialSimulatorDir
  $form.Controls.Add($pathTextBox)

  $browseButton = New-Object System.Windows.Forms.Button
  $browseButton.Location = New-Object System.Drawing.Point(762, 88)
  $browseButton.Size = New-Object System.Drawing.Size(104, 32)
  $browseButton.Anchor = "Top,Right"
  $browseButton.Text = "浏览..."
  $form.Controls.Add($browseButton)

  $hintLabel = New-Object System.Windows.Forms.Label
  $hintLabel.Location = New-Object System.Drawing.Point(18, 126)
  $hintLabel.Size = New-Object System.Drawing.Size(848, 20)
  $hintLabel.Anchor = "Top,Left,Right"
  $hintLabel.Text = "请选择包含 *_compile.do、*_elaborate.do、*_simulate.do、simulate.bat 的目录，生成文件会放到其上一级目录。"
  $form.Controls.Add($hintLabel)

  $generateButton = New-Object System.Windows.Forms.Button
  $generateButton.Location = New-Object System.Drawing.Point(18, 162)
  $generateButton.Size = New-Object System.Drawing.Size(120, 32)
  $generateButton.Text = "生成脚本"
  $form.Controls.Add($generateButton)

  $closeButton = New-Object System.Windows.Forms.Button
  $closeButton.Location = New-Object System.Drawing.Point(150, 162)
  $closeButton.Size = New-Object System.Drawing.Size(90, 32)
  $closeButton.Text = "关闭"
  $form.Controls.Add($closeButton)

  $statusLabel = New-Object System.Windows.Forms.Label
  $statusLabel.Location = New-Object System.Drawing.Point(258, 166)
  $statusLabel.Size = New-Object System.Drawing.Size(608, 24)
  $statusLabel.Anchor = "Top,Left,Right"
  $statusLabel.Text = "等待选择目录。"
  $form.Controls.Add($statusLabel)

  $logLabel = New-Object System.Windows.Forms.Label
  $logLabel.Location = New-Object System.Drawing.Point(18, 214)
  $logLabel.Size = New-Object System.Drawing.Size(120, 22)
  $logLabel.Text = "运行日志"
  $form.Controls.Add($logLabel)

  $logTextBox = New-Object System.Windows.Forms.TextBox
  $logTextBox.Location = New-Object System.Drawing.Point(18, 240)
  $logTextBox.Size = New-Object System.Drawing.Size(848, 268)
  $logTextBox.Anchor = "Top,Bottom,Left,Right"
  $logTextBox.Multiline = $true
  $logTextBox.ScrollBars = "Vertical"
  $logTextBox.ReadOnly = $true
  $logTextBox.WordWrap = $false
  $logTextBox.Font = New-Object System.Drawing.Font("Consolas", 10)
  $form.Controls.Add($logTextBox)

  $browseButton.Add_Click({
    $initialBrowseDir = ""
    if (-not [string]::IsNullOrWhiteSpace($pathTextBox.Text) -and (Test-Path -LiteralPath $pathTextBox.Text)) {
      $initialBrowseDir = (Resolve-Path -LiteralPath $pathTextBox.Text).Path
    }
    else {
      $initialBrowseDir = (Resolve-Path -LiteralPath (Get-Location).Path).Path
    }

    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Title = "请选择 questa/modelsim 目录"
    $dialog.InitialDirectory = $initialBrowseDir
    $dialog.Filter = "文件夹选择占位|*.folder"
    $dialog.CheckFileExists = $false
    $dialog.CheckPathExists = $true
    $dialog.ValidateNames = $false
    $dialog.FileName = "请选择此目录"
    $dialog.RestoreDirectory = $true

    if ($dialog.ShowDialog($form) -eq [System.Windows.Forms.DialogResult]::OK) {
      $selectedPath = Split-Path -Parent $dialog.FileName
      if ([string]::IsNullOrWhiteSpace($selectedPath)) {
        $selectedPath = $initialBrowseDir
      }

      $pathTextBox.Text = $selectedPath
      Write-GenerationLog -Message "已选择目录 / Selected directory: $selectedPath" -LogBox $logTextBox
      $statusLabel.Text = "目录已选择，等待生成。"
    }
  })

  $closeButton.Add_Click({
    $form.Close()
  })

  $generateAction = {
    try {
      $form.Cursor = [System.Windows.Forms.Cursors]::WaitCursor
      $generateButton.Enabled = $false
      $statusLabel.Text = "处理中..."

      $selectedDir = $pathTextBox.Text.Trim()
      if ([string]::IsNullOrWhiteSpace($selectedDir)) {
        throw "请先选择要处理的 questa/modelsim 目录。"
      }

      $candidateSelectionCallback = {
        param($SelectionContext)
        return Show-MemoryCandidateSelectionDialog -Owner $form -SelectionContext $SelectionContext
      }

      $result = Generate-MySimArtifacts -SimulatorDir $selectedDir -OutTclName $OutTclName -OutBatName $OutBatName -LogBox $logTextBox -CandidateSelectionCallback $candidateSelectionCallback
      $statusLabel.Text = "生成完成，输出位于上一级目录。"
      Write-GenerationLog -Message "请注意放置位置 / Keep the generated BAT and TCL in: $($result.OutputDir)" -LogBox $logTextBox
      Show-GenerationCompletion -Owner $form -Result $result
    }
    catch {
      $statusLabel.Text = "生成失败。"
      Write-GenerationLog -Message ("生成失败 / Generation failed: {0}" -f $_.Exception.Message) -LogBox $logTextBox
      [System.Windows.Forms.MessageBox]::Show(
        $form,
        $_.Exception.Message,
        "生成失败 / Generation Failed",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
      ) | Out-Null
    }
    finally {
      $form.Cursor = [System.Windows.Forms.Cursors]::Default
      $generateButton.Enabled = $true
    }
  }

  $generateButton.Add_Click($generateAction)
  $form.AcceptButton = $generateButton
  $form.CancelButton = $closeButton

  [void]$form.ShowDialog()
}

if ($NoUi -or -not [string]::IsNullOrWhiteSpace($SimulatorDir)) {
  $result = Generate-MySimArtifacts -SimulatorDir $SimulatorDir -OutTclName $OutTclName -OutBatName $OutBatName
  Write-Host ""
  Write-Host "完成。输出文件位于上一级目录 / Completed. Output files are in the parent directory:"
  Write-Host "  $($result.OutputTcl)"
  Write-Host "  $($result.OutputBat)"
  Write-Host "请保持这两个文件放在上述上一级目录，不要移动回 questa/modelsim 目录。"
}
else {
  Show-GeneratorUi -InitialSimulatorDir $SimulatorDir -OutTclName $OutTclName -OutBatName $OutBatName
}
