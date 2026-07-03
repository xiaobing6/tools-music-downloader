from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_script_runs_frontend_build_before_nuitka() -> None:
    script = (ROOT / "scripts/build_exe.ps1").read_text(encoding="utf-8")

    assert "$frontendDir" in script
    assert "npm.cmd --prefix $frontendDir install" in script
    assert "npm.cmd --prefix $frontendDir run build" in script
    assert "$staticIndex" in script
    assert "--include-data-dir=music_downloader/gui/static=music_downloader/gui/static" in script
