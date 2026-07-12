param(
    [ValidateSet("standalone", "onefile")]
    [string]$Mode = "onefile",
    [switch]$SkipInstall,
    [ValidateRange(1, 256)]
    [int]$Jobs = [Math]::Min([System.Environment]::ProcessorCount, 8)
)

function Assert-ExitCode {
    param([string]$Stage, [int]$ExitCode)
    if ($ExitCode -ne 0) {
        throw "$Stage failed with exit code $ExitCode"
    }
}

function Write-Sha256Manifest {
    param(
        [string]$Root,
        [string[]]$FilePaths,
        [string]$ManifestPath
    )

    $lines = foreach ($filePath in ($FilePaths | Sort-Object)) {
        $fullPath = [System.IO.Path]::GetFullPath($filePath)
        $relativePath = $fullPath.Substring($Root.Length).TrimStart([char[]]"\/")
        $relativePath = $relativePath.Replace('\', '/')
        $hash = Get-FileHash -LiteralPath $filePath -Algorithm SHA256
        "$($hash.Hash.ToLowerInvariant())  $relativePath"
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($ManifestPath, [string[]]$lines, $utf8NoBom)
}

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$previousNuitkaCacheDir = $env:NUITKA_CACHE_DIR
$locationPushed = $false

Push-Location $ProjectRoot
$locationPushed = $true
try {
    $pythonVersion = python -c "import sys; print('.'.join(map(str, sys.version_info[:3]))); raise SystemExit(sys.version_info < (3, 11))"
    if ($LASTEXITCODE -ne 0) {
        throw "Python 3.11+ is required. Current Python: $pythonVersion"
    }

    $readVersionCode =
@'
import tomllib
with open('pyproject.toml', 'rb') as f:
    print(tomllib.load(f)['project']['version'])
'@
    $ProjectVersion = python -c $readVersionCode
    Assert-ExitCode "Project version read" $LASTEXITCODE

    $constraintsFile = Join-Path $ProjectRoot "requirements-build-constraints.txt"
    if (-not $SkipInstall) {
        python -m pip install -r requirements-build.txt -c $constraintsFile
        Assert-ExitCode "Build dependency installation" $LASTEXITCODE
    } else {
        Write-Host "Skipping dependency installs (SkipInstall mode). Using already-installed tools." -ForegroundColor Yellow
    }

    $frontendDir = Join-Path $ProjectRoot "music_downloader/gui/frontend"
    $staticIndex = Join-Path $ProjectRoot "music_downloader/gui/static/index.html"
    $iconPath = Join-Path $ProjectRoot "music_downloader/gui/assets/music_downloader.ico"
    if (-not (Test-Path -LiteralPath $frontendDir -PathType Container)) {
        throw "Frontend source directory is missing: $frontendDir"
    }
    if (-not (Test-Path -LiteralPath $iconPath -PathType Leaf)) {
        throw "Application icon not found: $iconPath"
    }

    $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCommand) {
        throw "npm.cmd was not found. Install Node.js before building the GUI exe."
    }

    if (-not $SkipInstall) {
        npm.cmd --prefix $frontendDir ci
        Assert-ExitCode "Frontend dependency installation" $LASTEXITCODE
    } elseif (-not (Test-Path -LiteralPath (Join-Path $frontendDir "node_modules") -PathType Container)) {
        throw "Frontend dependencies are missing. Run npm.cmd --prefix music_downloader/gui/frontend install, or build without -SkipInstall."
    }

    npm.cmd --prefix $frontendDir run build
    if ($LASTEXITCODE -ne 0) {
        throw "Frontend build failed with exit code $LASTEXITCODE"
    }
    if (-not (Test-Path -LiteralPath $staticIndex -PathType Leaf)) {
        throw "Frontend build did not produce expected artifact: $staticIndex"
    }

    $env:NUITKA_CACHE_DIR = Join-Path $ProjectRoot ".nuitka-cache"
    New-Item -ItemType Directory -Force -Path $env:NUITKA_CACHE_DIR | Out-Null

    $nodeVersion = node --version
    Assert-ExitCode "Node.js version check" $LASTEXITCODE
    $npmVersion = npm.cmd --version
    Assert-ExitCode "npm version check" $LASTEXITCODE
    $nuitkaVersion = python -m nuitka --version
    Assert-ExitCode "Nuitka version check" $LASTEXITCODE
    Write-Host "Python: $pythonVersion"
    Write-Host "Node.js: $nodeVersion"
    Write-Host "npm: $npmVersion"
    Write-Host "Nuitka: $($nuitkaVersion -join ' ')"

    $distDir = Join-Path $ProjectRoot "dist"
    $stagingDir = Join-Path $ProjectRoot "dist-staging"
    $backupDir = Join-Path $ProjectRoot "dist-backup"
    $standaloneDir = Join-Path $stagingDir "music_download.dist"

    if (Test-Path -LiteralPath $backupDir) {
        throw "Build backup directory already exists; recover or remove it before building: $backupDir"
    }
    if (Test-Path -LiteralPath $stagingDir) {
        Remove-Item -LiteralPath $stagingDir -Recurse -Force
    }

    $isCi = ($env:CI -eq "true") -or ($env:GITHUB_ACTIONS -eq "true")
    $commonArgs = @(
        "--disable-plugin=pywebview",
        "--include-module=webview.platforms.winforms",
        "--include-module=webview.platforms.win32",
        "--include-module=webview.platforms.edgechromium",
        "--include-module=webview.platforms.mshtml",
        "--playwright-include-browser=none",
        "--nofollow-import-to=playwright.async_api",
        "--output-dir=$stagingDir",
        "--output-filename=music_download.exe",
        "--msvc=latest",
        "--jobs=$Jobs",
        "--windows-product-name=music_download",
        "--windows-file-version=$ProjectVersion",
        "--windows-company-name=tools-music-downloader",
        "--windows-file-description=Music downloader CLI and GUI tool",
        "--windows-console-mode=hide",
        "--windows-icon-from-ico=$iconPath",
        "--include-data-file=music_downloader/gui/assets/music_downloader.ico=music_downloader/gui/assets/music_downloader.ico",
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
        $stagedExe = Join-Path $stagingDir "music_download.exe"
    } else {
        python -m nuitka --mode=standalone @commonArgs
        $stagedExe = Join-Path $standaloneDir "music_download.exe"
    }
    Assert-ExitCode "Nuitka build" $LASTEXITCODE
    if (-not (Test-Path -LiteralPath $stagedExe -PathType Leaf)) {
        throw "Build did not produce expected artifact: $stagedExe"
    }

    $intermediateDirs = @(
        (Join-Path $stagingDir "music_download.build"),
        (Join-Path $stagingDir "music_download.onefile-build")
    )
    if ($Mode -eq "onefile") {
        $intermediateDirs += $standaloneDir
    }
    foreach ($dir in $intermediateDirs) {
        if (Test-Path -LiteralPath $dir) {
            Remove-Item -LiteralPath $dir -Recurse -Force
        }
    }

    & $stagedExe --help
    Assert-ExitCode "Packaged executable smoke test" $LASTEXITCODE

    $manifestPath = Join-Path $stagingDir "SHA256SUMS.txt"
    if ($Mode -eq "onefile") {
        $artifactFiles = @($stagedExe)
    } else {
        $artifactFiles = @(
            Get-ChildItem -LiteralPath $standaloneDir -File -Recurse |
                ForEach-Object { $_.FullName }
        )
    }
    Write-Sha256Manifest -Root $stagingDir -FilePaths $artifactFiles -ManifestPath $manifestPath

    $distMovedToBackup = $false
    try {
        if (Test-Path -LiteralPath $distDir) {
            Move-Item -LiteralPath $distDir -Destination $backupDir
            $distMovedToBackup = $true
        }
        Move-Item -LiteralPath $stagingDir -Destination $distDir
        if ($distMovedToBackup) {
            Remove-Item -LiteralPath $backupDir -Recurse -Force
        }
    } catch {
        if ($distMovedToBackup) {
            if (Test-Path -LiteralPath $distDir) {
                Remove-Item -LiteralPath $distDir -Recurse -Force
            }
            Move-Item -LiteralPath $backupDir -Destination $distDir
        }
        throw
    }

    $outputExe = if ($Mode -eq "onefile") {
        Join-Path $distDir "music_download.exe"
    } else {
        Join-Path $distDir "music_download.dist/music_download.exe"
    }
    Write-Host ""
    Write-Host "Build finished." -ForegroundColor Green
    Write-Host "Output: $outputExe"
    Write-Host "Checksums: $(Join-Path $distDir 'SHA256SUMS.txt')"
} finally {
    $stagingDir = Join-Path $ProjectRoot "dist-staging"
    if (Test-Path -LiteralPath $stagingDir) {
        Remove-Item -LiteralPath $stagingDir -Recurse -Force
    }
    if ($null -eq $previousNuitkaCacheDir) {
        Remove-Item Env:NUITKA_CACHE_DIR -ErrorAction SilentlyContinue
    } else {
        $env:NUITKA_CACHE_DIR = $previousNuitkaCacheDir
    }
    if ($locationPushed) {
        Pop-Location
    }
}
