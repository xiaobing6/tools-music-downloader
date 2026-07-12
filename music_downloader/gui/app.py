"""GUI application entry point.

Creates the pywebview window, loads the frontend, and starts the event loop.
"""

from __future__ import annotations

import contextlib
import os
import sys
import threading
from pathlib import Path

DEFAULT_WINDOW_SIZE = (1280, 800)
MIN_WINDOW_SIZE = (1024, 720)


def _candidate_static_dirs(
    module_file: str | os.PathLike[str] | None = None,
    executable: str | os.PathLike[str] | None = None,
) -> list[Path]:
    """Return possible GUI static directories for source and Nuitka builds."""
    module_path = Path(module_file if module_file is not None else __file__).resolve()
    executable_path = Path(executable if executable is not None else sys.argv[0]).resolve()

    candidates = [
        module_path.parent / "static",
        executable_path.parent / "music_downloader" / "gui" / "static",
        executable_path.parent / "static",
    ]

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        if candidate not in seen:
            unique_candidates.append(candidate)
            seen.add(candidate)
    return unique_candidates


def _get_static_dir(
    module_file: str | os.PathLike[str] | None = None,
    executable: str | os.PathLike[str] | None = None,
) -> str:
    """Resolve static resources for source, standalone, and onefile runs."""
    candidates = _candidate_static_dirs(module_file=module_file, executable=executable)
    for candidate in candidates:
        if (candidate / "index.html").exists():
            return str(candidate)
    return str(candidates[0])


def _candidate_icon_paths(
    module_file: str | os.PathLike[str] | None = None,
    executable: str | os.PathLike[str] | None = None,
) -> list[Path]:
    """Return possible application icon paths for source and Nuitka builds."""
    module_path = Path(module_file if module_file is not None else __file__).resolve()
    executable_path = Path(executable if executable is not None else sys.argv[0]).resolve()
    icon_name = "music_downloader.ico"

    candidates = [
        module_path.parent / "assets" / icon_name,
        executable_path.parent / "music_downloader" / "gui" / "assets" / icon_name,
        executable_path.parent / "assets" / icon_name,
    ]

    return list(dict.fromkeys(candidates))


def _get_icon_path(
    module_file: str | os.PathLike[str] | None = None,
    executable: str | os.PathLike[str] | None = None,
) -> str | None:
    """Resolve the desktop application icon when it is available."""
    for candidate in _candidate_icon_paths(module_file=module_file, executable=executable):
        if candidate.is_file():
            return str(candidate)
    return None


def _format_missing_static_message(html_path: str, candidates: list[Path]) -> str:
    checked = "\n".join(f"  - {candidate / 'index.html'}" for candidate in candidates)
    return f"错误: 找不到 GUI 资源文件: {html_path}\n已检查:\n{checked}"


def run_gui() -> None:
    """Start the desktop GUI application."""
    import webview

    from music_downloader.gui.api import MusicApi
    from music_downloader.gui.settings import load_config

    config = load_config()
    api = MusicApi()

    static_dir = _get_static_dir()
    html_path = os.path.join(static_dir, "index.html")

    if not os.path.exists(html_path):
        print(_format_missing_static_message(html_path, _candidate_static_dirs()), file=sys.stderr)
        print(
            "请先构建 GUI 前端，或确认 music_downloader/gui/static/ 包含 index.html",
            file=sys.stderr,
        )
        sys.exit(1)

    width = int(config.get("window_width", DEFAULT_WINDOW_SIZE[0]))
    height = int(config.get("window_height", DEFAULT_WINDOW_SIZE[1]))
    width = max(width, MIN_WINDOW_SIZE[0])
    height = max(height, MIN_WINDOW_SIZE[1])

    window = webview.create_window(
        title="音乐下载器",
        url=html_path,
        width=width,
        height=height,
        min_size=MIN_WINDOW_SIZE,
        resizable=True,
        confirm_close=False,
        js_api=api,
        text_select=True,
    )
    api.set_window(window)

    def on_closing() -> bool:
        if api.consume_close_confirmation():
            return True
        threading.Thread(
            target=api.request_close_confirmation,
            name="close-confirmation-request",
            daemon=True,
        ).start()
        return False

    def on_closed() -> None:
        with contextlib.suppress(Exception):
            api.shutdown()

    if window is not None:
        window.events.closing += on_closing
        window.events.closed += on_closed

    webview.start(debug=False, icon=_get_icon_path())
