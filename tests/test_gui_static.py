from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "music_downloader/gui/static"
FRONTEND_SRC = ROOT / "music_downloader/gui/frontend/src"


def test_vite_static_entry_exists() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")

    assert 'id="app"' in html
    assert 'type="module"' in html
    assert "assets/" in html


def test_vite_static_assets_exist() -> None:
    assets_dir = STATIC / "assets"

    assert assets_dir.exists()
    assert any(path.suffix == ".js" for path in assets_dir.iterdir())
    assert any(path.suffix == ".css" for path in assets_dir.iterdir())


def test_retry_failed_controls_exist_in_svelte_source() -> None:
    source = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_SRC.rglob("*.svelte"))

    assert 'id="retryFailedBtn"' in source
    assert 'data-testid="retry-failed"' in source
    assert "failedIndices" in source
    assert "retryFailed" in source
