# Install Python packages and FFmpeg into this repo's .venv, then register the MCP clients.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

function Get-BasePython {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return @{ File = "py"; Extra = @("-3") }
    }
    foreach ($name in @("python", "python3")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return @{ File = $cmd.Source; Extra = @() } }
    }
    return $null
}

function Install-LocalPython {
    $dest = Join-Path $Root ".python"
    $exe = Join-Path $dest "python.exe"
    if (Test-Path $exe) { return $exe }
    $installer = Join-Path $Root ".python-installer.exe"
    $url = "https://www.python.org/ftp/python/3.13.7/python-3.13.7-amd64.exe"
    Write-Host "Downloading Python into $dest"
    Invoke-WebRequest -Uri $url -OutFile $installer
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $args = @(
        "/quiet", "InstallAllUsers=0", "PrependPath=0", "Include_test=0",
        "Include_launcher=0", "Include_pip=1", "Shortcuts=0", "TargetDir=$dest"
    )
    $proc = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
    if ($proc.ExitCode -ne 0) { throw "Python installer exited $($proc.ExitCode)" }
    Remove-Item $installer -Force
    if (-not (Test-Path $exe)) { throw "Python was not installed at $exe" }
    return $exe
}

$base = Get-BasePython
if (-not (Test-Path (Join-Path $Root ".venv\Scripts\python.exe"))) {
    if ($base) {
        & $base.File @($base.Extra) -m venv (Join-Path $Root ".venv")
    } else {
        $local = Install-LocalPython
        & $local -m venv (Join-Path $Root ".venv")
    }
}

$py = Join-Path $Root ".venv\Scripts\python.exe"
& $py -m pip install -U pip
& $py -m pip install -e $Root
& $py -m video_editor.install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
