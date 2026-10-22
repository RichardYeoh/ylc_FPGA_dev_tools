# Resolve stable local runtimes for startup wrappers / 为自启动包装脚本解析稳定的本地运行时
function Resolve-CodexPowerShell {
    $stablePowerShell = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
    if (Test-Path -LiteralPath $stablePowerShell) {
        return $stablePowerShell
    }

    $pwshCommand = Get-Command pwsh.exe -ErrorAction SilentlyContinue
    if ($pwshCommand -and (Test-Path -LiteralPath $pwshCommand.Path)) {
        return $pwshCommand.Path
    }

    $powershellCommand = Get-Command powershell.exe -ErrorAction SilentlyContinue
    if ($powershellCommand -and (Test-Path -LiteralPath $powershellCommand.Path)) {
        return $powershellCommand.Path
    }

    throw "No usable PowerShell executable was found"
}

function Resolve-CodexPythonw {
    $pythonwCommand = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($pythonwCommand -and (Test-Path -LiteralPath $pythonwCommand.Path)) {
        return $pythonwCommand.Path
    }

    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $pythonwCandidate = Join-Path (Split-Path -Parent $pythonCommand.Path) "pythonw.exe"
        if (Test-Path -LiteralPath $pythonwCandidate) {
            return $pythonwCandidate
        }
    }

    $candidates = @(
        (Join-Path $env:LocalAppData "Programs\Python\Python313\pythonw.exe"),
        (Join-Path $env:LocalAppData "Programs\Python\Python312\pythonw.exe"),
        (Join-Path $env:ProgramFiles "Python313\pythonw.exe"),
        (Join-Path $env:ProgramFiles "Python312\pythonw.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $pythonRoots = @(
        "HKCU:\Software\Python\PythonCore",
        "HKLM:\Software\Python\PythonCore",
        "HKLM:\Software\WOW6432Node\Python\PythonCore"
    )
    foreach ($pythonRoot in $pythonRoots) {
        foreach ($version in (Get-ChildItem -LiteralPath $pythonRoot -ErrorAction SilentlyContinue | Sort-Object Name -Descending)) {
            $installPath = (Get-ItemProperty -LiteralPath $version.PSPath -Name InstallPath -ErrorAction SilentlyContinue).InstallPath
            if ($installPath) {
                $pythonwCandidate = Join-Path $installPath "pythonw.exe"
                if (Test-Path -LiteralPath $pythonwCandidate) {
                    return $pythonwCandidate
                }
            }
        }
    }

    throw "No usable Python interpreter was found"
}
