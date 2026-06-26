"""Python API exposed to the frontend JS via pywebview bridge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from music_downloader.config import SEARCH_TYPE_MAP, VALID_BITRATES, VALID_FORMATS, VALID_SOURCES
from music_downloader.gui.bridge import MusicBridge
from music_downloader.gui.settings import DEFAULT_CONFIG, load_config, save_config


class MusicApi:
    """API class exposed to JavaScript as window.pywebview.api.

    All public methods are callable from the frontend. The _emit method
    dispatches CustomEvent('py-log' / 'py-progress') to the window so
    the frontend can listen for real-time updates.
    """

    def __init__(self) -> None:
        self._window: Any = None
        self._bridge = MusicBridge(
            on_log=self._handle_log,
            on_progress=self._handle_progress,
        )

    def set_window(self, window: Any) -> None:
        self._window = window

    def _handle_log(self, msg: str, level: str) -> None:
        self._emit("log", {"message": msg, "level": level})

    def _handle_progress(self, data: dict[str, Any]) -> None:
        self._emit("progress", data)

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self._window is not None:
            try:
                payload = json.dumps(data, ensure_ascii=False)
                js_code = (
                    f"window.dispatchEvent(new CustomEvent('py-{event}', {{detail: {payload}}}));"
                )
                self._window.evaluate_js(js_code)
            except Exception:
                pass

    def get_config(self) -> dict[str, Any]:
        return load_config()

    def save_config(self, config: dict[str, Any]) -> bool:
        try:
            save_config(config)
            return True
        except Exception:
            return False

    def get_valid_options(self) -> dict[str, Any]:
        return {
            "sources": [{"value": s, "label": _SOURCE_LABELS.get(s, s)} for s in VALID_SOURCES],
            "bitrates": VALID_BITRATES,
            "search_types": list(SEARCH_TYPE_MAP.keys()),
            "formats": VALID_FORMATS,
        }

    def init_browser(self) -> dict[str, Any]:
        ok = self._bridge.ensure_browser()
        return {"ready": ok}

    def search(
        self, keyword: str, source: str, search_type: str, number: int
    ) -> list[dict[str, Any]]:
        try:
            num = int(number)
            if num < 1:
                num = DEFAULT_CONFIG["number"]
        except (TypeError, ValueError):
            num = DEFAULT_CONFIG["number"]
        return self._bridge.search(keyword, source, search_type, num)

    def start_download(
        self,
        songs: list[dict[str, Any]],
        source: str,
        bitrate: str,
        download_lyric: bool,
        download_cover: bool,
        output_dir: str,
    ) -> str:
        if not output_dir:
            config = load_config()
            output_dir = config.get(
                "output_dir", str(Path.home() / "Downloads" / "MusicDownloader")
            )
        os.makedirs(output_dir, exist_ok=True)
        return self._bridge.start_download(
            songs=songs,
            source=source,
            bitrate=bitrate,
            download_lyric=download_lyric,
            download_cover=download_cover,
            output_dir=output_dir,
        )

    def cancel_download(self, task_id: str) -> None:
        self._bridge.cancel_download(task_id)

    def open_download_dir(self, path: str = "") -> None:
        target = path or load_config().get("output_dir", str(Path.home() / "Downloads"))
        if not os.path.exists(target):
            os.makedirs(target, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception:
            pass

    def select_directory(self) -> str:
        try:
            from tkinter import Tk, filedialog

            root = Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            path = filedialog.askdirectory(title="选择下载目录")
            root.destroy()
            return path if path else ""
        except Exception:
            return ""

    def check_environment(self) -> list[dict[str, Any]]:
        return self._bridge.check_environment()

    def get_history(self) -> list[dict[str, Any]]:
        return self._bridge.get_history()

    def shutdown(self) -> None:
        self._bridge.shutdown()


_SOURCE_LABELS: dict[str, str] = {
    "netease": "网易云音乐",
    "migu": "咪咕音乐",
    "kuwo": "酷我音乐",
    "ytmusic": "YouTube Music",
    "tidal": "Tidal",
    "qobuz": "Qobuz",
    "deezer": "Deezer",
    "spotify": "Spotify",
    "tencent": "QQ音乐",
    "ximalaya": "喜马拉雅",
    "joox": "Joox",
    "apple": "Apple Music",
}
