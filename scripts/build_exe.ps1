param(
    [ValidateSet("standalone", "onefile")]
    [string]$Mode = "onefile",
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

# 从 pyproject.toml 读取版本号，避免多处硬编码
# 使用 here-string 避免 PowerShell 解析引号/逗号/冒号
$readVersionCode =
@'
import tomllib
with open('pyproject.toml', 'rb') as f:
    print(tomllib.load(f)['project']['version'])
'@
$ProjectVersion = python -c $readVersionCode
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

# Decide whether to allow Nuitka to download toolchain components:
#   * CI (GitHub Actions, etc.) is a clean runner with nothing cached, so we
#     MUST allow downloads or Nuitka aborts with "no (default non-interactive)".
#   * Local builds use MSVC (located via Windows registry, no download needed),
#     so auto-download is disabled to avoid silently fetching extras.
$isCi = ($env:CI -eq 'true') -or ($env:GITHUB_ACTIONS -eq 'true')

$commonArgs = @(
    "--playwright-include-browser=none",
    "--nofollow-import-to=playwright.async_api",
    "--output-dir=dist",
    "--output-filename=music_download.exe",
    "--msvc=latest",
    "--jobs=$([System.Environment]::ProcessorCount)",
    "--windows-product-name=music_download",
    "--windows-file-version=$ProjectVersion",
    "--windows-company-name=tools-music-downloader",
    "--windows-file-description=CLI music search and download tool",
    "--include-data-dir=music_downloader/gui/static=music_downloader/gui/static"
)
if ($isCi) {
    Write-Host "CI mode: enabling --assume-yes-for-downloads for toolchain setup." -ForegroundColor Yellow
    $commonArgs = @("--assume-yes-for-downloads") + $commonArgs
} else {
    Write-Host "Local mode: using MSVC from Visual Studio installation." -ForegroundColor Cyan
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

# 清理中间构建目录，只保留最终 exe
$intermediateDirs = @(
    (Join-Path $ProjectRoot "dist/music_download.build"),
    (Join-Path $ProjectRoot "dist/music_download.dist"),
    (Join-Path $ProjectRoot "dist/music_download.onefile-build")
)
foreach ($dir in $intermediateDirs) {
    if (Test-Path $dir) {
        Remove-Item $dir -Recurse -Force
    }
}

Write-Host ""
Write-Host "Build finished." -ForegroundColor Green
Write-Host "Output: $expectedExe"
