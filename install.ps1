# Install Python for the current user when it is missing, then FFmpeg into .venv.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Find-PythonExe {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $out = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out -and ($out -notlike "*\WindowsApps\*")) {
            return $out.Trim()
        }
    }
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if ($cmd.Source -like "*\WindowsApps\*") { continue }
        $out = & $cmd.Source -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out -and ($out -notlike "*\WindowsApps\*")) {
            return $out.Trim()
        }
    }
    return $null
}

function Install-UserPython {
    $dest = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313"
    $exe = Join-Path $dest "python.exe"
    if (Test-Path $exe) {
        & $exe -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { return $exe }
    }
    $installer = Join-Path $env:TEMP "python-3.13.7-amd64.exe"
    $url = "https://www.python.org/ftp/python/3.13.7/python-3.13.7-amd64.exe"
    Write-Host "Python is not found. Downloading Python 3.13.7 for the current user."
    Invoke-WebRequest -Uri $url -OutFile $installer
    $proc = Start-Process -FilePath $installer -ArgumentList @(
        "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1",
        "Include_test=0", "Include_launcher=1", "Shortcuts=0", "TargetDir=$dest"
    ) -Wait -PassThru
    Remove-Item $installer -Force -ErrorAction SilentlyContinue
    if ($proc.ExitCode -ne 0 -or -not (Test-Path $exe)) {
        [Console]::Error.WriteLine("Python could not be installed (installer exit $($proc.ExitCode)).")
        exit 1
    }
    Write-Host "Installed Python at $exe"
    return $exe
}

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    $base = Find-PythonExe
    if (-not $base) { $base = Install-UserPython }
    & $base -m venv (Join-Path $Root ".venv")
}

& $venvPy -m pip install -U pip
& $venvPy -m pip install -e $Root
& $venvPy -m video_editor.install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
