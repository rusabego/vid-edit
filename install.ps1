# Unpack Python into .python when this PC has none, then install FFmpeg into .venv.
# The package is a zip. The EXE setup exits 1603 on some PCs, so this script never launches it.
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
} catch {}
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Test-PythonExe {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $false }
    if ($Path -like "*\WindowsApps\*") { return $false }
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    & $Path -c "import sys, venv, ensurepip; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
    return $LASTEXITCODE -eq 0
}

function Find-PythonExe {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py -and $py.Source -notlike "*\WindowsApps\*") {
        $out = & py -3 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            $exe = @($out)[-1].ToString().Trim()
            if (Test-PythonExe $exe) { return $exe }
        }
    }
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if (-not $cmd) { continue }
        if (Test-PythonExe $cmd.Source) { return $cmd.Source }
    }

    $parents = @()
    if ($env:LOCALAPPDATA) { $parents += (Join-Path $env:LOCALAPPDATA "Programs\Python") }
    if ($env:ProgramFiles) { $parents += (Join-Path $env:ProgramFiles "Python") }
    if (${env:ProgramFiles(x86)}) { $parents += (Join-Path ${env:ProgramFiles(x86)} "Python") }
    foreach ($parent in $parents) {
        if (-not (Test-Path -LiteralPath $parent)) { continue }
        $found = @(Get-ChildItem -LiteralPath $parent -Filter python.exe -Recurse -Depth 2 -ErrorAction SilentlyContinue)
        foreach ($item in $found) {
            if (Test-PythonExe $item.FullName) { return $item.FullName }
        }
    }

    $patterns = @()
    if ($env:ProgramFiles) { $patterns += (Join-Path $env:ProgramFiles "Python*\python.exe") }
    if (${env:ProgramFiles(x86)}) { $patterns += (Join-Path ${env:ProgramFiles(x86)} "Python*\python.exe") }
    $patterns += "C:\Python*\python.exe"
    foreach ($pattern in $patterns) {
        foreach ($item in @(Get-Item -Path $pattern -ErrorAction SilentlyContinue)) {
            if (Test-PythonExe $item.FullName) { return $item.FullName }
        }
    }

    $local = Join-Path $Root ".python\python.exe"
    if (Test-PythonExe $local) { return $local }
    return $null
}

function Install-BundledPython {
    $dest = Join-Path $Root ".python"
    $exe = Join-Path $dest "python.exe"
    if (Test-PythonExe $exe) { return $exe }

    $arch = $env:PROCESSOR_ARCHITECTURE
    if ($arch -eq "x86" -and $env:PROCESSOR_ARCHITEW6432) { $arch = $env:PROCESSOR_ARCHITEW6432 }
    if ($arch -ne "AMD64" -and $arch -ne "ARM64") {
        [Console]::Error.WriteLine("Python could not be installed. This download is the 64-bit build, and this PC is $arch.")
        exit 1
    }

    $work = Join-Path $env:TEMP ("video-editor-python-" + [guid]::NewGuid().ToString("n"))
    $unpack = Join-Path $work "unpack"
    $nupkg = Join-Path $work "python.nupkg"
    $url = "https://www.nuget.org/api/v2/package/python/3.13.7"
    New-Item -ItemType Directory -Path $unpack | Out-Null
    try {
        Write-Host "Python is not found. Downloading Python 3.13.7 into .python."
        try {
            Invoke-WebRequest -Uri $url -OutFile $nupkg -UseBasicParsing
        } catch {
            [Console]::Error.WriteLine("Python could not be downloaded. $($_.Exception.Message)")
            exit 1
        }
        if (-not (Test-Path -LiteralPath $nupkg) -or (Get-Item -LiteralPath $nupkg).Length -lt 1000) {
            [Console]::Error.WriteLine("Python could not be downloaded.")
            exit 1
        }
        $head = [System.IO.File]::ReadAllBytes($nupkg)[0..1]
        if ($head[0] -ne 80 -or $head[1] -ne 75) {
            [Console]::Error.WriteLine("Python could not be downloaded. The file was not a package.")
            exit 1
        }
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($nupkg, $unpack)
        $tools = Join-Path $unpack "tools"
        if (-not (Test-Path -LiteralPath (Join-Path $tools "python.exe"))) {
            [Console]::Error.WriteLine("Python could not be installed. The package had no python.exe.")
            exit 1
        }
        if (Test-Path -LiteralPath $dest) { Remove-Item -LiteralPath $dest -Recurse -Force }
        Move-Item -LiteralPath $tools -Destination $dest
    } finally {
        if (Test-Path -LiteralPath $work) {
            Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    if (-not (Test-PythonExe $exe)) {
        [Console]::Error.WriteLine("Python could not be installed.")
        exit 1
    }
    Write-Host "Installed Python at $exe"
    return $exe
}

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPy)) {
    $base = Find-PythonExe
    if (-not $base) { $base = Install-BundledPython }
    & $base -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $venvPy)) {
        [Console]::Error.WriteLine("Could not create .venv.")
        exit 1
    }
}

& $venvPy -m pip install -U pip
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $venvPy -m pip install -e $Root
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& $venvPy -m video_editor.install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
