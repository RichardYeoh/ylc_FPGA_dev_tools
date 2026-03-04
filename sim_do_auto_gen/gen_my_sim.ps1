param(
  [string]$QuestaDir = "",
  [string]$OutDoName = "my_sim.do",
  [string]$OutBatName = "my_sim.bat"
)

$ErrorActionPreference = "Stop"

function Write-Utf8NoBomFile {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][AllowEmptyCollection()][AllowEmptyString()][string[]]$Lines
  )

  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $text = ($Lines -join "`r`n") + "`r`n"
  [System.IO.File]::WriteAllText($Path, $text, $utf8NoBom)
}

function Resolve-ExistingWaveBlock {
  param([string]$MySimDoPath)

  $defaultBlock = @(
    "#user wave-watch add here",
    "# add wave -position insertpoint sim:/<tb>/<path>/*",
    "#user wave-watch add here end"
  )

  if (-not (Test-Path -LiteralPath $MySimDoPath)) {
    return $defaultBlock
  }

  $lines = Get-Content -LiteralPath $MySimDoPath
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

function Resolve-ExistingRunLine {
  param([string]$MySimDoPath)

  $defaultRun = "run 100ms"
  if (-not (Test-Path -LiteralPath $MySimDoPath)) {
    return $defaultRun
  }

  $line = Get-Content -LiteralPath $MySimDoPath | Where-Object { $_ -match "^\s*run\s+\S+" } | Select-Object -Last 1
  if ([string]::IsNullOrWhiteSpace($line)) {
    return $defaultRun
  }

  return $line.Trim()
}

function Resolve-DefaultQuestaDir {
  param([string]$ScriptDir)

  # Expected location:
  #   <proj>.srcs\sim_1\sim_do_auto_gen\gen_my_sim.ps1
  # Try to infer:
  #   <proj>.sim\sim_1\behav\questa
  $sim1Dir = (Resolve-Path (Join-Path $ScriptDir "..")).Path
  $srcsDir = (Resolve-Path (Join-Path $sim1Dir "..")).Path
  $workRoot = Split-Path -Parent $srcsDir
  $srcsName = Split-Path -Leaf $srcsDir

  $candidateDirs = @()

  if ($srcsName -like "*.srcs") {
    $projName = $srcsName.Substring(0, $srcsName.Length - 5)
    if (-not [string]::IsNullOrWhiteSpace($projName)) {
      $candidateDirs += Join-Path $workRoot ("{0}.sim\sim_1\behav\questa" -f $projName)
    }
  }

  $candidateDirs += Get-ChildItem -LiteralPath $workRoot -Directory -Filter "*.sim" |
    ForEach-Object { Join-Path $_.FullName "sim_1\behav\questa" }

  $existing = @(
    $candidateDirs |
    Select-Object -Unique |
    Where-Object { Test-Path -LiteralPath $_ }
  )

  if ($existing.Count -eq 0) {
    throw "Cannot auto-detect Questa directory. Please pass -QuestaDir explicitly."
  }

  if ($existing.Count -eq 1) {
    return $existing[0]
  }

  # Prefer the candidate derived from sibling '<proj>.srcs' -> '<proj>.sim'
  if ($srcsName -like "*.srcs") {
    $projName = $srcsName.Substring(0, $srcsName.Length - 5)
    $preferred = Join-Path $workRoot ("{0}.sim\sim_1\behav\questa" -f $projName)
    if (Test-Path -LiteralPath $preferred) {
      return $preferred
    }
  }

  # Fallback: choose the most recently updated candidate.
  $latest = $existing |
    ForEach-Object { Get-Item -LiteralPath $_ } |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  return $latest.FullName
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if ([string]::IsNullOrWhiteSpace($QuestaDir)) {
  $QuestaDir = Resolve-DefaultQuestaDir -ScriptDir $scriptDir
}

if (-not (Test-Path -LiteralPath $QuestaDir)) {
  throw "Questa directory does not exist: $QuestaDir"
}

$QuestaDir = (Resolve-Path $QuestaDir).Path

$compileCandidates = Get-ChildItem -LiteralPath $QuestaDir -File -Filter "*_compile.do" | Sort-Object LastWriteTime -Descending
if ($compileCandidates.Count -eq 0) {
  throw "No '*_compile.do' found in: $QuestaDir"
}

$compileDo = $compileCandidates[0]
$baseName = $compileDo.BaseName -replace "_compile$", ""
$elaborateDo = Join-Path $QuestaDir ($baseName + "_elaborate.do")
$simulateDo = Join-Path $QuestaDir ($baseName + "_simulate.do")
$simulateBat = Join-Path $QuestaDir "simulate.bat"

foreach ($f in @($elaborateDo, $simulateDo, $simulateBat)) {
  if (-not (Test-Path -LiteralPath $f)) {
    throw "Required file not found: $f"
  }
}

$outDoPath = Join-Path $QuestaDir $OutDoName
$outBatPath = Join-Path $QuestaDir $OutBatName

$waveBlock = Resolve-ExistingWaveBlock -MySimDoPath $outDoPath
$runLine = Resolve-ExistingRunLine -MySimDoPath $outDoPath

$compileLines = Get-Content -LiteralPath $compileDo.FullName | Where-Object { $_ -notmatch "^\s*quit\s+-force\s*$" }
$elaborateBody = Get-Content -LiteralPath $elaborateDo | Where-Object {
  $_ -notmatch "^\s*$" -and
  $_ -notmatch "^\s*#" -and
  $_ -notmatch "^\s*quit\s+-force\s*$"
}

$simulateBody = @()
foreach ($line in (Get-Content -LiteralPath $simulateDo)) {
  if ($line -match "^\s*$") { continue }
  if ($line -match "^\s*#") { continue }
  if ($line -match "^\s*quit\s+-force\s*$") { continue }
  if ($line -match "^\s*do\s+\{.*_wave\.do\}\s*$") { continue }
  if ($line -match "^\s*do\s+\{.*\.udo\}\s*$") { continue }
  if ($line -match "^\s*run\s+\S+") { continue }
  if ($line -match "^\s*view\s+\S+") { continue }
  $simulateBody += $line
}

$created = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
$compileDoName = [System.IO.Path]::GetFileName($compileDo.FullName)
$elaborateDoName = [System.IO.Path]::GetFileName($elaborateDo)
$simulateDoName = [System.IO.Path]::GetFileName($simulateDo)

$outDoLines = @(
  "######################################################################",
  "#",
  "# File name : $OutDoName",
  "# Created on: $created",
  "#",
  "# EN: Auto merged from $compileDoName, $elaborateDoName, $simulateDoName",
  "# CN: 自动合并来源为 $compileDoName, $elaborateDoName, $simulateDoName",
  "# EN: Generated by gen_my_sim.ps1 and overwritten on each rerun.",
  "# CN: 由 gen_my_sim.ps1 生成，每次重新运行都会覆盖同名输出文件。",
  "#",
  "######################################################################",
  "",
  "######################################################################",
  "# EN: Section A - Compile and library setup.",
  "# CN: 段A - 编译与库映射配置。",
  "# EN: Source = $compileDoName (copied as-is except trailing 'quit -force').",
  "# CN: 来源 = $compileDoName（基本原样复制，仅去掉末尾 'quit -force'）。",
  "######################################################################",
  ""
)

$outDoLines += $compileLines
$outDoLines += @(
  "",
  "######################################################################",
  "# EN: Section B - Elaboration command.",
  "# CN: 段B - 设计展开命令。",
  "# EN: Source = $elaborateDoName (comments, blank lines, and 'quit -force' removed).",
  "# CN: 来源 = $elaborateDoName（去掉注释、空行和 'quit -force'）。",
  "######################################################################",
  "",
  "#$elaborateDoName"
)

$outDoLines += $elaborateBody
$outDoLines += @(
  "",
  "######################################################################",
  "# EN: Section C - Simulation startup core commands.",
  "# CN: 段C - 仿真启动核心命令。",
  "# EN: Source = $simulateDoName (wave/udo/view/run lines removed to allow custom control).",
  "# CN: 来源 = $simulateDoName（去除 wave/udo/view/run 行，以便自定义控制）。",
  "######################################################################",
  "",
  "#$simulateDoName"
)

$outDoLines += $simulateBody
$outDoLines += @(
  "",
  "######################################################################",
  "# EN: Section D - User wave block.",
  "# CN: 段D - 用户波形配置块。",
  "# EN: Preserved from existing my_sim.do if markers exist; otherwise template is inserted.",
  "# CN: 若旧 my_sim.do 中存在标记则保留原块，否则插入模板块。",
  "######################################################################",
  ""
)

$outDoLines += $waveBlock
$outDoLines += @(
  "",
  "######################################################################",
  "# EN: Section E - Viewer and runtime control.",
  "# CN: 段E - 波形窗口与运行时长控制。",
  "# EN: Runtime line is preserved from existing my_sim.do when available.",
  "# CN: 运行时长优先沿用旧 my_sim.do 的 run 行。",
  "######################################################################",
  "",
  "view wave",
  "view structure",
  "view signals",
  "",
  "#user decide sim time",
  $runLine
)

Write-Utf8NoBomFile -Path $outDoPath -Lines $outDoLines

$binPath = "d:\questasim64_10.6c\win64"
$binLine = Get-Content -LiteralPath $simulateBat | Where-Object { $_ -match "^\s*set\s+bin_path\s*=" } | Select-Object -First 1
if ($binLine -match "^\s*set\s+bin_path\s*=\s*(.+?)\s*$") {
  $binPath = $matches[1]
}

$outBatLines = @(
  "@echo off",
  "REM EN: Auto generated by gen_my_sim.ps1",
  "REM CN: 由 gen_my_sim.ps1 自动生成",
  "REM EN: This launcher runs my_sim.do in Questa and is overwritten on each rerun.",
  "REM CN: 此启动脚本用于在 Questa 执行 my_sim.do，每次重新生成会覆盖本文件。",
  "REM EN: bin_path source = simulate.bat (fallback to default if not found).",
  "REM CN: bin_path 来源 = simulate.bat（若未找到则使用默认值）。",
  "set bin_path=$binPath",
  "call %bin_path%/vsim   -do ""do {$OutDoName}"" -l simulate.log",
  "if ""%errorlevel%""==""1"" goto END",
  "if ""%errorlevel%""==""0"" goto SUCCESS",
  ":END",
  "exit 1",
  ":SUCCESS",
  "exit 0"
)

Write-Utf8NoBomFile -Path $outBatPath -Lines $outBatLines

Write-Host "Generated:"
Write-Host "  $outDoPath"
Write-Host "  $outBatPath"
