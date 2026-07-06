from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_script_runs_frontend_build_before_nuitka() -> None:
    script = (ROOT / "scripts/build_exe.ps1").read_text(encoding="utf-8")

    assert '$frontendDir = Join-Path $ProjectRoot "music_downloader/gui/frontend"' in script
    assert (
        '$staticIndex = Join-Path $ProjectRoot "music_downloader/gui/static/index.html"' in script
    )
    assert "Frontend source directory is missing" in script
    assert "Get-Command npm.cmd" in script
    assert "npm.cmd was not found" in script
    assert "npm.cmd --prefix $frontendDir install" in script
    assert "npm.cmd --prefix $frontendDir run build" in script
    assert "Frontend dependencies are missing" in script
    assert "Frontend build failed" in script
    assert "Frontend build did not produce expected artifact: $staticIndex" in script
    assert "--disable-plugin=pywebview" in script
    assert "--include-module=webview.platforms.winforms" in script
    assert "--include-module=webview.platforms.win32" in script
    assert "--include-module=webview.platforms.edgechromium" in script
    assert "--include-module=webview.platforms.mshtml" in script
    assert "--windows-console-mode=hide" in script
    assert "--windows-console-mode=attach" not in script
    assert "--include-data-dir=music_downloader/gui/static=music_downloader/gui/static" in script

    frontend_build_position = script.index("npm.cmd --prefix $frontendDir run build")
    static_check_position = script.index("Frontend build did not produce expected artifact")
    nuitka_cache_position = script.index("$env:NUITKA_CACHE_DIR")
    nuitka_command_position = script.index("python -m nuitka")

    assert frontend_build_position < static_check_position < nuitka_cache_position
    assert static_check_position < nuitka_command_position
