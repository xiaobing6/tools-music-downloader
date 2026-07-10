from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "scripts/build_exe.ps1").read_text(encoding="utf-8")


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
        "--include-data-dir=music_downloader/gui/static=music_downloader/gui/static",
    ):
        assert argument in SCRIPT
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
    expected = {
        "playwright==1.60.0",
        "mutagen==1.48.0",
        "rich==15.0.0",
        "typer==0.26.8",
        "pydantic==2.13.4",
        "pywebview==6.2.1",
        "nuitka==4.1.3",
        "ordered-set==4.1.0",
        "zstandard==0.25.0",
    }
    assert expected <= set(constraints.splitlines())
