param(
    [ValidateSet("standalone", "onefile")]
    [string]$Mode = "onefile",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $SkipInstall) {
    # 幂等安装构建依赖
    python -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install build dependencies (exit $LASTEXITCODE)"
    }
} else {
    Write-Host "Skipping pip install (SkipInstall mode). Using already-installed tools." -ForegroundColor Yellow
}

$env:NUITKA_CACHE_DIR = Join-Path $ProjectRoot ".nuitka-cache"
New-Item -ItemType Directory -Force -Path $env:NUITKA_CACHE_DIR | Out-Null

# Deliberately do NOT pass --assume-yes-for-downloads / --downloads:
# Nuitka may silently fetch depends.exe (dependencywalker) or other external tools.
# The repo rule is "no new build tools" - keep auto-download disabled.
# If something is actually needed, install it manually or add --include-* flags explicitly.
$commonArgs = @(
    "--enable-plugin=anti-bloat",
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

# 校验产物确实存在
$expectedExe = Join-Path $ProjectRoot "dist/music_download.exe"
if (-not (Test-Path $expectedExe)) {
    throw "Build did not produce expected artifact: $expectedExe"
}

Write-Host ""
Write-Host "Build finished." -ForegroundColor Green
Write-Host "Output: $expectedExe"
