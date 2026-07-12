from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts/build_exe.ps1").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")


def test_build_script_runs_frontend_build_before_nuitka() -> None:
    assert '$frontendDir = Join-Path $ProjectRoot "music_downloader/gui/frontend"' in SCRIPT
    assert (
        '$staticIndex = Join-Path $ProjectRoot "music_downloader/gui/static/index.html"' in SCRIPT
    )
    assert "Get-Command npm.cmd" in SCRIPT
    assert "npm.cmd --prefix $frontendDir ci" in SCRIPT
    assert "npm.cmd --prefix $frontendDir run build" in SCRIPT
    assert "Frontend dependencies are missing" in SCRIPT
    assert "Frontend build failed" in SCRIPT
    assert "Frontend build did not produce expected artifact: $staticIndex" in SCRIPT

    frontend_build_position = SCRIPT.index("npm.cmd --prefix $frontendDir run build")
    static_check_position = SCRIPT.index("Frontend build did not produce expected artifact")
    nuitka_command_position = SCRIPT.index("python -m nuitka --mode=")
    assert frontend_build_position < static_check_position < nuitka_command_position


def test_build_script_keeps_required_nuitka_options() -> None:
    for argument in (
        "--disable-plugin=pywebview",
        "--include-module=webview.platforms.winforms",
        "--include-module=webview.platforms.win32",
        "--include-module=webview.platforms.edgechromium",
        "--include-module=webview.platforms.mshtml",
        "--playwright-include-browser=none",
        "--windows-console-mode=hide",
        "--windows-icon-from-ico=$iconPath",
        "--include-data-dir=music_downloader/gui/static=music_downloader/gui/static",
        "--include-data-file=music_downloader/gui/assets/music_downloader.ico=music_downloader/gui/assets/music_downloader.ico",
    ):
        assert argument in SCRIPT
    assert (
        '$iconPath = Join-Path $ProjectRoot "music_downloader/gui/assets/music_downloader.ico"'
        in SCRIPT
    )
    assert "Application icon not found: $iconPath" in SCRIPT
    assert "--windows-console-mode=attach" not in SCRIPT


def test_build_script_has_reproducible_and_bounded_inputs() -> None:
    assert "[ValidateRange(1, 256)]" in SCRIPT
    assert "[Math]::Min([System.Environment]::ProcessorCount, 8)" in SCRIPT
    assert "requirements-build-constraints.txt" in SCRIPT
    assert "python -m pip install -r requirements-build.txt -c $constraintsFile" in SCRIPT
    assert "sys.version_info < (3, 11)" in SCRIPT
    assert "python -m nuitka --version" in SCRIPT


def test_build_script_stages_and_promotes_mode_specific_outputs() -> None:
    assert '$stagingDir = Join-Path $ProjectRoot "dist-staging"' in SCRIPT
    assert '$backupDir = Join-Path $ProjectRoot "dist-backup"' in SCRIPT
    assert '$standaloneDir = Join-Path $stagingDir "music_download.dist"' in SCRIPT
    assert '$stagedExe = Join-Path $standaloneDir "music_download.exe"' in SCRIPT
    assert '$stagedExe = Join-Path $stagingDir "music_download.exe"' in SCRIPT
    assert "Move-Item -LiteralPath $stagingDir -Destination $distDir" in SCRIPT


def test_build_script_smoke_tests_and_hashes_artifacts() -> None:
    assert "& $stagedExe --help" in SCRIPT
    assert "Get-FileHash -LiteralPath $filePath -Algorithm SHA256" in SCRIPT
    assert '$manifestPath = Join-Path $stagingDir "SHA256SUMS.txt"' in SCRIPT
    assert "Write-Sha256Manifest" in SCRIPT


def test_build_constraints_pin_direct_dependencies() -> None:
    constraints = (ROOT / "requirements-build-constraints.txt").read_text(encoding="utf-8")
    expected = (
        "playwright==1.60.0",
        "mutagen==1.48.0",
        "rich==15.0.0",
        "typer==0.26.8",
        "pydantic==2.13.4",
        "pywebview==6.2.1",
        "nuitka==4.1.3",
        "ordered-set==4.1.0",
        "zstandard==0.25.0",
    )
    actual = tuple(
        line.strip()
        for line in constraints.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )
    assert actual == expected


def test_readme_documents_process_scoped_execution_policy_troubleshooting() -> None:
    assert (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
        r".\scripts\build_exe.ps1" in README
    )
    assert "仅对本次 PowerShell 进程生效" in README
    assert "不要通过 `Set-ExecutionPolicy` 修改用户级或计算机级策略" in README


WINDOWS_ONLY = pytest.mark.skipif(os.name != "nt", reason="PowerShell build script is Windows-only")


def _assert_build_script_failure_handling(tmp_path: Path, scenario: str) -> None:
    project_root = tmp_path / "project"
    scripts_dir = project_root / "scripts"
    frontend_dir = project_root / "music_downloader" / "gui" / "frontend"
    static_dir = project_root / "music_downloader" / "gui" / "static"
    assets_dir = project_root / "music_downloader" / "gui" / "assets"
    scripts_dir.mkdir(parents=True)
    frontend_dir.mkdir(parents=True)
    static_dir.mkdir(parents=True)
    assets_dir.mkdir(parents=True)
    (frontend_dir / "node_modules").mkdir()
    (static_dir / "index.html").write_text("stub", encoding="utf-8")
    (assets_dir / "music_downloader.ico").write_bytes(b"icon-stub")
    (scripts_dir / "build_exe.ps1").write_text(SCRIPT, encoding="utf-8")
    (project_root / "pyproject.toml").write_text('[project]\nversion = "0.0.0"\n', encoding="utf-8")

    dist_dir = project_root / "dist"
    dist_dir.mkdir()
    (dist_dir / "previous-build.txt").write_text("preserve", encoding="utf-8")
    if scenario == "stale-backup":
        backup_dir = project_root / "dist-backup"
        backup_dir.mkdir()
        (backup_dir / "recovery-needed.txt").write_text("preserve", encoding="utf-8")

    wrapper = tmp_path / "invoke-build.ps1"
    wrapper.write_text(
        r"""param(
    [Parameter(Mandatory = $true)]
    [string]$BuildScript,
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot,
    [Parameter(Mandatory = $true)]
    [ValidateSet("promotion-failure", "stale-backup")]
    [string]$Scenario
)

$ErrorActionPreference = "Stop"
$initialLocation = (Get-Location).Path
$initialCacheDir = "test-cache-sentinel"
$env:NUITKA_CACHE_DIR = $initialCacheDir
$global:promotionFailureInjected = $false

function python {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Arguments)

    $argumentText = $Arguments -join " "
    if ($argumentText -match "sys.version_info") {
        "3.11.9"
    } elseif ($argumentText -match "tomllib") {
        "0.0.0"
    } elseif ($argumentText -eq "-m nuitka --version") {
        "4.1.3"
    } elseif ($argumentText -match "-m nuitka --mode=onefile") {
        $outputArgument = @($Arguments | Where-Object { "$_" -like "--output-dir=*" })[0]
        $outputDirectory = "$outputArgument".Substring("--output-dir=".Length)
        New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null
        Copy-Item -LiteralPath "$env:SystemRoot\System32\cmd.exe" -Destination (
            Join-Path $outputDirectory "music_download.exe"
        )
    } else {
        throw "Unexpected python invocation: $argumentText"
    }
    $global:LASTEXITCODE = 0
}

function npm.cmd {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Arguments)

    if (($Arguments -join " ") -eq "--version") {
        "10.0.0"
    }
    $global:LASTEXITCODE = 0
}

function node {
    param([Parameter(ValueFromRemainingArguments = $true)][object[]]$Arguments)

    if (($Arguments -join " ") -ne "--version") {
        throw "Unexpected node invocation: $($Arguments -join ' ')"
    }
    "v22.0.0"
    $global:LASTEXITCODE = 0
}

function Move-Item {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)][string]$LiteralPath,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    if (
        $Scenario -eq "promotion-failure" -and
        (Split-Path -Leaf $LiteralPath) -eq "dist-staging" -and
        (Split-Path -Leaf $Destination) -eq "dist"
    ) {
        $global:promotionFailureInjected = $true
        throw "Injected staging promotion failure"
    }
    Microsoft.PowerShell.Management\Move-Item @PSBoundParameters
}

try {
    & $BuildScript -SkipInstall
    throw "Build unexpectedly succeeded"
} catch {
    if ($Scenario -eq "promotion-failure") {
        if (-not $promotionFailureInjected) {
            throw "Promotion failure was not injected: $($_.Exception.Message)"
        }
        if ($_.Exception.Message -notlike "*Injected staging promotion failure*") {
            throw
        }
    } elseif ($_.Exception.Message -notlike "*Build backup directory already exists*") {
        throw
    }
}

if ((Get-Location).Path -ne $initialLocation) {
    throw "Build script did not restore the caller location"
}
if ($env:NUITKA_CACHE_DIR -ne $initialCacheDir) {
    throw "Build script did not restore NUITKA_CACHE_DIR"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "dist/previous-build.txt") -PathType Leaf)) {
    throw "Previous dist contents were not preserved"
}
if (Test-Path -LiteralPath (Join-Path $ProjectRoot "dist-staging")) {
    throw "Staging directory was not cleaned"
}
if ($Scenario -eq "promotion-failure") {
    if (Test-Path -LiteralPath (Join-Path $ProjectRoot "dist-backup")) {
        throw "Rollback backup was not cleaned"
    }
} elseif (-not (Test-Path -LiteralPath (Join-Path $ProjectRoot "dist-backup/recovery-needed.txt") -PathType Leaf)) {
    throw "Stale backup was unexpectedly modified"
}
""",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(wrapper),
            "-BuildScript",
            str(scripts_dir / "build_exe.ps1"),
            "-ProjectRoot",
            str(project_root),
            "-Scenario",
            scenario,
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert (dist_dir / "previous-build.txt").read_text(encoding="utf-8") == "preserve"
    assert not (project_root / "dist-staging").exists()
    if scenario == "promotion-failure":
        assert not (project_root / "dist-backup").exists()
    else:
        assert (project_root / "dist-backup" / "recovery-needed.txt").exists()


@WINDOWS_ONLY
def test_build_script_rolls_back_failed_promotion(tmp_path: Path) -> None:
    _assert_build_script_failure_handling(tmp_path, "promotion-failure")


@WINDOWS_ONLY
def test_build_script_refuses_stale_backup(tmp_path: Path) -> None:
    _assert_build_script_failure_handling(tmp_path, "stale-backup")
