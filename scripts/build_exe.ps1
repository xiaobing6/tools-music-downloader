param(
    [ValidateSet("standalone", "onefile")]
    [string]$Mode = "onefile"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:NUITKA_CACHE_DIR = Join-Path $ProjectRoot ".nuitka-cache"
New-Item -ItemType Directory -Force -Path $env:NUITKA_CACHE_DIR | Out-Null

$commonArgs = @(
    "--assume-yes-for-downloads",
    "--enable-plugin=pylint-warnings",
    "--playwright-include-browser=none",
    "--output-dir=dist",
    "--output-filename=music_download.exe",
    "music_download.py"
)

if ($Mode -eq "onefile") {
    python -m nuitka --mode=onefile @commonArgs
} else {
    python -m nuitka --mode=standalone @commonArgs
}

if ($LASTEXITCODE -ne 0) {
    throw "Nuitka build failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Build finished." -ForegroundColor Green
Write-Host "Output directory: $ProjectRoot\dist"
