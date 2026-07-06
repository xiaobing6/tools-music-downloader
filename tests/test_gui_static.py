from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "music_downloader/gui/static"
FRONTEND_SRC = ROOT / "music_downloader/gui/frontend/src"


class AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.module_scripts: list[str] = []
        self.stylesheets: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "script" and attributes.get("type") == "module" and attributes.get("src"):
            self.module_scripts.append(attributes["src"])
        if tag == "link" and attributes.get("rel") == "stylesheet" and attributes.get("href"):
            self.stylesheets.append(attributes["href"])


def _static_asset_path(reference: str) -> Path:
    parsed = urlparse(reference)
    assert parsed.scheme == ""
    assert parsed.netloc == ""
    relative = unquote(parsed.path).lstrip("./")
    path = (STATIC / relative).resolve()
    assert path.is_relative_to(STATIC.resolve())
    return path


def test_vite_static_entry_exists() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    parser = AssetParser()
    parser.feed(html)

    assert 'id="app"' in html
    assert parser.module_scripts
    assert parser.stylesheets
    assert all("assets/" in reference for reference in parser.module_scripts + parser.stylesheets)


def test_vite_static_assets_exist() -> None:
    assets_dir = STATIC / "assets"

    assert assets_dir.is_dir()
    assert any(path.suffix == ".js" for path in assets_dir.iterdir())
    assert any(path.suffix == ".css" for path in assets_dir.iterdir())


def test_vite_static_entry_references_existing_assets() -> None:
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    parser = AssetParser()
    parser.feed(html)

    for reference in parser.module_scripts + parser.stylesheets:
        assert _static_asset_path(reference).is_file()


def test_retry_failed_controls_exist_in_svelte_source() -> None:
    result_list = (FRONTEND_SRC / "lib/components/ResultList.svelte").read_text(encoding="utf-8")
    app = (FRONTEND_SRC / "App.svelte").read_text(encoding="utf-8")

    assert 'id="retryFailedBtn"' in result_list
    assert 'data-testid="retry-failed"' in result_list
    assert "failedIndices" in app
    assert "async function retryFailed" in app
    assert "onclick={onRetryFailed}" in result_list
    assert "onRetryFailed={retryFailed}" in app
