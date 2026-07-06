"""GUI application entry point.

Creates the pywebview window, loads the frontend, and starts the event loop.
"""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path

DEFAULT_WINDOW_SIZE = (1266, 1013)
MIN_WINDOW_SIZE = (1266, 1013)


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
        js_api=api,
        text_select=True,
    )
    api.set_window(window)

    def on_closing() -> None:
        with contextlib.suppress(Exception):
            api.shutdown()

    if window is not None:
        window.events.closing += on_closing

    webview.start(debug=False)
