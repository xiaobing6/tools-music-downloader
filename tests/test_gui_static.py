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
    assert 'class="min-h-0 flex-1 overflow-auto scrollbar-thin"' not in app
    assert 'class="flex h-full min-h-0 flex-col' in result_list
    assert (
        'class="min-h-0 flex-1 divide-y divide-slate-100 overflow-auto scrollbar-thin"'
        in result_list
    )
    assert 'class="flex min-h-0 flex-1' in empty_state
    assert "flex min-h-0 flex-1 flex-col" in log_panel
    assert 'id="logContent" class="min-h-0 flex-1' in log_panel
    assert "max-h-60" not in log_panel


def test_result_list_uses_compact_library_rows() -> None:
    result_list = (FRONTEND_SRC / "lib/components/ResultList.svelte").read_text(encoding="utf-8")
    search_bar = (FRONTEND_SRC / "lib/components/SearchBar.svelte").read_text(encoding="utf-8")
    app = (FRONTEND_SRC / "App.svelte").read_text(encoding="utf-8")
    css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")

    assert 'class="result-columns"' in result_list
    assert 'class="result-row"' in result_list
    assert "data-selected=" in result_list
    assert 'width="40"' in result_list
    assert 'height="40"' in result_list
    assert "—" in result_list
    assert "min-height: 60px;" in css
    assert (
        "grid-template-columns: 16px 40px minmax(190px, 1fr) "
        "minmax(180px, 0.95fr) minmax(150px, 0.72fr) 64px;"
    ) in css
    assert 'data-selected="true"' in css
    assert "下载选中{selectedCount" not in result_list
    assert "resultCount" not in search_bar
    assert "resultCount={songs.length}" not in app


def test_search_feedback_and_source_labels_use_shared_frontend_state() -> None:
    app = (FRONTEND_SRC / "App.svelte").read_text(encoding="utf-8")
    search_bar = (FRONTEND_SRC / "lib/components/SearchBar.svelte").read_text(encoding="utf-8")
    result_list = (FRONTEND_SRC / "lib/components/ResultList.svelte").read_text(encoding="utf-8")

    assert 'let searchFeedback = $state("")' in app
    assert 'let searchAnnouncement = $state("")' in app
    assert "feedback={searchFeedback}" in app
    assert "sourceOptions={options.sources}" in app
    assert "searchAnnouncement={searchAnnouncement}" in app
    assert 'id="searchFeedback"' in search_bar
    assert "aria-invalid={Boolean(feedback)}" in search_bar
    assert 'aria-live="polite"' in result_list
    assert "sourceOptions" in result_list
    assert "const labels: Record<string, string>" not in result_list
    assert 'netease: "网易云音乐"' not in result_list


def test_result_rows_only_outline_keyboard_focus() -> None:
    css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")

    assert ".result-row:has(input:focus-visible)" in css
    assert ".result-row:focus-within" not in css


def test_app_shell_fills_pywebview_client_area_without_fixed_minimums() -> None:
    css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")
    shell_block = css.split(".app-shell {", 1)[1].split("}", 1)[0]

    assert "width: 100%;" in shell_block
    assert "height: 100%;" in shell_block
    assert "min-width:" not in shell_block
    assert "min-height:" not in shell_block
    assert "height: 100vh;" not in shell_block


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
    assert "visible:" not in app
    assert "visible: boolean" not in types
    assert "{#if progress.visible}" not in progress_panel
    assert '<section id="downloadPanel"' in progress_panel
    assert "cancelable={downloadActive}" in app
    assert "cancelable: boolean" in progress_panel
    assert "{#if cancelable}" in progress_panel


def test_download_progress_long_labels_do_not_push_actions() -> None:
    progress_panel = (FRONTEND_SRC / "lib/components/DownloadProgress.svelte").read_text(
        encoding="utf-8"
    )

    assert 'class="min-w-0"' in progress_panel
    assert 'id="progressLabel" class="truncate' in progress_panel
    assert 'id="cancelDownloadBtn"' in progress_panel
    assert "shrink-0" in progress_panel


def test_startup_screen_uses_viewport_relative_layout() -> None:
    source = (FRONTEND_SRC / "lib/components/StartupScreen.svelte").read_text(encoding="utf-8")

    assert "min-height: 100%;" in source
    assert "display: flex;" in source
    assert "width: min(560px, calc(100% - 40px));" in source
    assert "width: min(360px, 100%);" in source
    assert "padding: clamp(" in source
    assert "height: clamp(" in source
    assert "width: 560px;" not in source
    assert "padding-top: 300px;" not in source
    assert "width: 360px;" not in source


def test_settings_selects_have_stable_custom_chevrons() -> None:
    settings = (FRONTEND_SRC / "lib/components/SettingsPanel.svelte").read_text(encoding="utf-8")
    css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")
    assert "select.select-input {" in css
    select_input_block = css.split("select.select-input {", 1)[1].split("}", 1)[0]

    assert "ChevronDown" in settings
    assert 'class="select-control"' in settings
    assert 'class="select-chevron"' in settings
    assert "appearance: none;" in select_input_block
    assert "background-image: none;" in select_input_block
    assert "select:open" in css


def test_workbench_uses_fixed_shell_with_internal_scrolling() -> None:
    css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")
    shell_block = css.split(".workbench-shell {", 1)[1].split("}", 1)[0]
    frame_block = css.split(".workbench-frame {", 1)[1].split("}", 1)[0]
    main_block = css.split(".workbench-main {", 1)[1].split("}", 1)[0]
    responsive = css.split("@media (max-width: 1179px)", 1)[1].split(
        "@media (max-width: 760px)", 1
    )[0]
    responsive_main = responsive.split(".workbench-main {", 1)[1].split("}", 1)[0]

    assert "overflow: hidden;" in shell_block
    assert "scrollbar-gutter" not in css
    assert "box-sizing: border-box;" in frame_block
    assert "height: 100%;" in frame_block
    assert "min-height: 0;" in frame_block
    assert "padding: 16px;" in frame_block
    assert "overflow: hidden;" in main_block
    assert "min-height: 0;" in responsive_main
    assert "overflow-y: auto;" in responsive_main
    assert "overscroll-behavior: contain;" in responsive_main
    assert "padding: 12px;" in responsive


def test_visual_polish_keeps_startup_compact_and_activity_grouped() -> None:
    startup = (FRONTEND_SRC / "lib/components/StartupScreen.svelte").read_text(encoding="utf-8")
    css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")

    assert "width: min(560px, calc(100% - 40px));" in startup
    assert "font-size: clamp(42px, 5vw, 48px);" in startup
    assert "opacity: 0.68;" in startup
    assert "background: rgba(255, 255, 255, 0.56);" in css


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
