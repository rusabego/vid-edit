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

$base = Get-BasePython
if (-not (Test-Path (Join-Path $Root ".venv\Scripts\python.exe"))) {
    if (-not $base) {
        [Console]::Error.WriteLine("Python is not found.")
        exit 1
    }
    & $base.File @($base.Extra) -m venv (Join-Path $Root ".venv")
}

$py = Join-Path $Root ".venv\Scripts\python.exe"
& $py -m pip install -U pip
& $py -m pip install -e $Root
& $py -m video_editor.install
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
