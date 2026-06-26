"""GUI application entry point.

Creates the pywebview window, loads the frontend, and starts the event loop.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def _get_static_dir() -> str:
    """Resolve the static resources directory, compatible with Nuitka onefile builds."""
    if "__compiled__" in globals():
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "static")


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
        print(f"错误: 找不到 GUI 资源文件: {html_path}", file=sys.stderr)
        print("请确认 music_downloader/gui/static/ 目录存在且包含 index.html", file=sys.stderr)
        sys.exit(1)

    width = int(config.get("window_width", 960))
    height = int(config.get("window_height", 680))

    window = webview.create_window(
        title="音乐下载器",
        url=html_path,
        width=width,
        height=height,
        min_size=(800, 560),
        resizable=True,
        js_api=api,
        text_select=True,
    )
    api.set_window(window)

    def on_closing(window: Any) -> None:
        try:
            api.shutdown()
        except Exception:
            pass

    window.events.closing += on_closing

    webview.start(debug=False)
