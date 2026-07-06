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
    relative = unquote(parsed.path)
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


def test_results_and_logs_share_resizable_bottom_layout() -> None:
    app = (FRONTEND_SRC / "App.svelte").read_text(encoding="utf-8")
    result_list = (FRONTEND_SRC / "lib/components/ResultList.svelte").read_text(encoding="utf-8")
    empty_state = (FRONTEND_SRC / "lib/components/EmptyState.svelte").read_text(encoding="utf-8")
    log_panel = (FRONTEND_SRC / "lib/components/LogPanel.svelte").read_text(encoding="utf-8")

    assert "items-stretch" in app
    assert 'class="min-h-0 flex-1 overflow-auto scrollbar-thin"' in app
    assert 'class="flex h-full min-h-0 flex-col' in result_list
    assert 'class="flex min-h-64 flex-1' in empty_state
    assert "flex min-h-0 flex-1 flex-col" in log_panel
    assert 'id="logContent" class="min-h-0 flex-1' in log_panel
    assert "max-h-60" not in log_panel


def test_app_shell_uses_window_minimum_size() -> None:
    css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")

    assert "min-width: 1266px;" in css
    assert "min-height: 1013px;" in css
    assert "min-width: 1200px;" not in css
    assert "min-height: 750px;" not in css


def test_environment_modal_is_centered() -> None:
    modal = (FRONTEND_SRC / "lib/components/EnvironmentModal.svelte").read_text(encoding="utf-8")

    assert 'placement="center"' in modal


def test_gui_progress_stays_visible_after_completion() -> None:
    app = (FRONTEND_SRC / "App.svelte").read_text(encoding="utf-8")
    progress_panel = (FRONTEND_SRC / "lib/components/DownloadProgress.svelte").read_text(
        encoding="utf-8"
    )
    types = (FRONTEND_SRC / "lib/types.ts").read_text(encoding="utf-8")

    assert "hideProgressTimer" not in app
    assert "setTimeout" not in app
    assert "visible:" not in app
    assert "visible: boolean" not in types
    assert "{#if progress.visible}" not in progress_panel
    assert '<section id="downloadPanel"' in progress_panel
    assert "cancelable={downloadActive}" in app
    assert "cancelable: boolean" in progress_panel
    assert "{#if cancelable}" in progress_panel


def test_gui_does_not_duplicate_backend_summary_logs() -> None:
    app = (FRONTEND_SRC / "App.svelte").read_text(encoding="utf-8")
    bridge = (ROOT / "music_downloader/gui/bridge.py").read_text(encoding="utf-8")

    assert 'self._emit_log(f"找到 {len(results)} 首歌曲", "success")' in bridge
    assert 'addLog(`找到 ${results.length} 首歌曲`, "success")' not in app
    assert 'f"下载完成: 成功 {task.success} / 失败 {task.fail} / 跳过 {task.skip}"' in bridge
    assert (
        "`下载完成: 成功 ${detail.success} / 失败 ${detail.fail} / 跳过 ${detail.skip}`" not in app
    )
    assert 'self._log("浏览器就绪，Cloudflare 验证通过", "success")' in bridge
    assert 'self._log("正在启动浏览器...", "info")' in bridge
    assert 'self._log("Cloudflare 验证未通过", "error")' in bridge
    assert 'addLog("正在初始化浏览器...", "info")' not in app
    assert 'addLog("浏览器已就绪", "success")' not in app
    assert 'addLog("浏览器初始化失败，请检查 Chrome 和网络环境", "error")' not in app
