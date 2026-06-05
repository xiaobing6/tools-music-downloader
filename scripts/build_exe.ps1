param(
    [ValidateSet("standalone", "onefile")]
    [string]$Mode = "onefile",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 从 pyproject.toml 读取版本号，避免多处硬编码
$ProjectVersion = python -c "import tomllib; print(tomllib.open('pyproject.toml','rb')['project']['version'])"
if ($LASTEXITCODE -ne 0) {
    throw "Failed to read version from pyproject.toml (exit $LASTEXITCODE)"
}

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

# 清理旧构建产物，避免残留混淆
$distDir = Join-Path $ProjectRoot "dist"
if (Test-Path $distDir) {
    Write-Host "Cleaning old dist directory..." -ForegroundColor Yellow
    Remove-Item $distDir -Recurse -Force
}

# Decide whether to allow Nuitka to fetch its toolchain (zig/scons/...):
#   * CI (GitHub Actions, etc.) is a clean runner with nothing cached, so we
#     MUST allow downloads or Nuitka aborts with "no (default non-interactive)".
#   * Local developer machines already have the toolchain cached, and the
#     repo rule is "no new build tools" - keep auto-download disabled so we
#     never silently fetch depends.exe or other extras.
$isCi = ($env:CI -eq 'true') -or ($env:GITHUB_ACTIONS -eq 'true')

$commonArgs = @(
    "--enable-plugin=anti-bloat",
    "--playwright-include-browser=none",
    "--output-dir=dist",
    "--output-filename=music_download.exe",
    "--lto=yes",
    "--jobs=$([System.Environment]::ProcessorCount)",
    "--windows-product-name=music_download",
    "--windows-file-version=$ProjectVersion",
    "--windows-company-name=tools-music-downloader",
    "--windows-file-description=命令行音乐搜索下载工具"
)
if ($isCi) {
    Write-Host "CI mode: enabling --assume-yes-for-downloads so Nuitka can fetch zig/scons." -ForegroundColor Yellow
    $commonArgs = @("--assume-yes-for-downloads") + $commonArgs
} else {
    Write-Host "Local mode: auto-downloads disabled. Make sure zig/scons are already installed." -ForegroundColor Yellow
}
$commonArgs += "music_download.py"

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
