from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_retry_failed_controls_exist() -> None:
    html = (ROOT / "music_downloader/gui/static/index.html").read_text(encoding="utf-8")
    js = (ROOT / "music_downloader/gui/static/js/app.js").read_text(encoding="utf-8")

    assert 'id="retryFailedBtn"' in html
    assert "failedIndices: new Set()" in js
    assert "function updateRetryFailedUI()" in js
    assert "function retryFailed()" in js
    assert "$('retryFailedBtn').addEventListener('click', retryFailed)" in js
