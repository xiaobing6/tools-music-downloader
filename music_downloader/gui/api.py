"""Python API exposed to the frontend JS via pywebview bridge."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from music_downloader.core.config import (
    SEARCH_TYPE_MAP,
    VALID_BITRATES,
    VALID_SOURCES,
)
from music_downloader.domain.enums import Bitrate, SearchType, Source
from music_downloader.domain.models import SearchOptions
from music_downloader.gui.bridge import MusicBridge
from music_downloader.gui.settings import DEFAULT_CONFIG, load_config, save_config

_CLOSE_DESTROY_DELAY_SECONDS = 0.05


class MusicApi:
    """API class exposed to JavaScript as window.pywebview.api.

    All public methods are callable from the frontend. The _emit method
    dispatches CustomEvent('py-log' / 'py-progress' / 'py-cover') to the window so
    the frontend can listen for real-time updates.
    """

    def __init__(self) -> None:
        self._window: Any = None
        self._close_confirmed = False
        self._bridge = MusicBridge(
            on_log=self._handle_log,
            on_progress=self._handle_progress,
            on_cover=self._handle_cover,
        )

    def set_window(self, window: Any) -> None:
        self._window = window

    def request_close_confirmation(self) -> None:
        self._emit("close-request", {})

    def consume_close_confirmation(self) -> bool:
        confirmed = self._close_confirmed
        self._close_confirmed = False
        return confirmed

    def confirm_close(self) -> None:
        if self._window is None:
            return
        self._close_confirmed = True
        window = self._window

        def destroy_window() -> None:
            try:
                window.destroy()
            except Exception:
                self._close_confirmed = False

        timer = threading.Timer(_CLOSE_DESTROY_DELAY_SECONDS, destroy_window)
        timer.daemon = True
        timer.start()

    def _handle_log(self, msg: str, level: str) -> None:
        self._emit("log", {"message": msg, "level": level})

    def _handle_progress(self, data: dict[str, Any]) -> None:
        self._emit("progress", data)

    def _handle_cover(self, data: dict[str, str]) -> None:
        self._emit("cover", data)

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
        }

    def init_browser(self) -> dict[str, Any]:
        ok = self._bridge.ensure_browser()
        return {"ready": ok}

    def search(
        self, keyword: str, source: str, search_type: str, number: int
    ) -> list[dict[str, Any]]:
        try:
            options = SearchOptions(
                keyword=keyword.strip(),
                source=Source(source),
                search_type=SearchType(search_type),
                number=int(number),
            )
        except (AttributeError, ValidationError, ValueError):
            return []
        return self._bridge.search(
            options.keyword,
            options.source.value,
            options.search_type.value,
            options.number,
        )

    def start_download(
        self,
        songs: list[dict[str, Any]],
        source: str,
        bitrate: str,
        download_lyric: bool,
        download_cover: bool,
        output_dir: str,
        keyword: str = "",
    ) -> str:
        try:
            validated_source = Source(source)
            validated_bitrate = Bitrate(bitrate)
        except ValueError:
            return ""
        if not output_dir:
            output_dir = load_config().get("output_dir", "")
        if not output_dir:
            output_dir = DEFAULT_CONFIG["output_dir"]
        return self._bridge.start_download(
            songs=songs,
            source=validated_source.value,
            bitrate=validated_bitrate.value,
            download_lyric=download_lyric,
            download_cover=download_cover,
            output_dir=output_dir,
            keyword=keyword.strip(),
        )

    def cancel_download(self, task_id: str) -> None:
        self._bridge.cancel_download(task_id)

    def open_download_dir(self, path: str = "") -> None:
        target = path or load_config().get("output_dir", str(Path.home() / "Downloads"))
        if not os.path.exists(target):
            os.makedirs(target, exist_ok=True)
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", str(target)])
                _center_explorer_window()
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception:
            pass

    def select_directory(self) -> str:
        if self._window is not None:
            try:
                import webview

                try:
                    dialog_type = webview.FileDialog.FOLDER
                except AttributeError:
                    dialog_type = webview.FOLDER_DIALOG
                _start_center_folder_dialog(self._window)
                paths = self._window.create_file_dialog(dialog_type=dialog_type)
                if isinstance(paths, str):
                    return paths
                if paths:
                    return str(paths[0])
                return ""
            except Exception:
                pass

        try:
            from tkinter import Tk, filedialog

            root = Tk()
            try:
                _center_tk_root(root)
                root.withdraw()
                root.attributes("-topmost", True)
                path = filedialog.askdirectory(title="选择下载目录", parent=root)
            finally:
                root.destroy()
            return path if path else ""
        except Exception:
            return ""

    def check_environment(self) -> list[dict[str, Any]]:
        return self._bridge.check_environment()

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

_FOLDER_DIALOG_TITLE_PARTS = (
    "\u9009\u62e9\u6587\u4ef6\u5939",
    "Select Folder",
    "Browse For Folder",
)
_FOLDER_DIALOG_CLASSES = {"#32770", "CabinetWClass"}


def _center_tk_root(root: Any) -> None:
    root.update_idletasks()
    width = 1
    height = 1
    x = max(0, (int(root.winfo_screenwidth()) - width) // 2)
    y = max(0, (int(root.winfo_screenheight()) - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")


def _start_center_folder_dialog(parent_window: Any | None) -> None:
    if sys.platform != "win32":
        return

    thread = threading.Thread(
        target=_center_folder_dialog_worker,
        args=(parent_window,),
        daemon=True,
    )
    thread.start()


def _center_folder_dialog_worker(parent_window: Any | None, timeout: float = 2.0) -> None:
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        parent_rect = _window_rect_from_pywebview(parent_window)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            hwnd = _find_window_by_title_and_class(
                user32,
                ctypes,
                wintypes,
                _FOLDER_DIALOG_TITLE_PARTS,
                _FOLDER_DIALOG_CLASSES,
            )
            if hwnd is not None and _center_window(
                hwnd,
                user32,
                ctypes,
                wintypes,
                center_area=parent_rect,
            ):
                return
            time.sleep(0.05)
    except Exception:
        return


def _window_rect_from_pywebview(window: Any | None) -> tuple[int, int, int, int] | None:
    if window is None:
        return None

    try:
        x = int(window.x)
        y = int(window.y)
        width = int(window.width)
        height = int(window.height)
    except Exception:
        return None

    if width <= 0 or height <= 0:
        return None
    return (x, y, x + width, y + height)


def _center_rect_in_work_area(
    window_rect: tuple[int, int, int, int],
    work_area: tuple[int, int, int, int],
) -> tuple[int, int]:
    window_left, window_top, window_right, window_bottom = window_rect
    work_left, work_top, work_right, work_bottom = work_area
    window_width = max(1, window_right - window_left)
    window_height = max(1, window_bottom - window_top)
    work_width = max(1, work_right - work_left)
    work_height = max(1, work_bottom - work_top)

    x = work_left + max(0, (work_width - window_width) // 2)
    y = work_top + max(0, (work_height - window_height) // 2)
    return x, y


def _center_explorer_window(timeout: float = 1.5) -> None:
    if sys.platform != "win32":
        return

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            hwnd = _find_window_by_class(
                user32,
                ctypes,
                wintypes,
                {"CabinetWClass", "ExploreWClass"},
            )
            if hwnd is not None and _center_window(hwnd, user32, ctypes, wintypes):
                return
            time.sleep(0.05)
    except Exception:
        return


def _find_window_by_class(
    user32: Any,
    ctypes_module: Any,
    wintypes_module: Any,
    class_names: set[str],
) -> int | None:
    matches: list[int] = []
    enum_windows_proc = ctypes_module.WINFUNCTYPE(
        wintypes_module.BOOL,
        wintypes_module.HWND,
        wintypes_module.LPARAM,
    )

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        class_name = ctypes_module.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, len(class_name))
        if class_name.value in class_names:
            matches.append(hwnd)
            return False
        return True

    user32.EnumWindows(enum_windows_proc(callback), 0)
    return matches[0] if matches else None


def _find_window_by_title_and_class(
    user32: Any,
    ctypes_module: Any,
    wintypes_module: Any,
    title_parts: tuple[str, ...],
    class_names: set[str],
) -> int | None:
    matches: list[int] = []
    enum_windows_proc = ctypes_module.WINFUNCTYPE(
        wintypes_module.BOOL,
        wintypes_module.HWND,
        wintypes_module.LPARAM,
    )

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True

        class_name = ctypes_module.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_name, len(class_name))
        if class_names and class_name.value not in class_names:
            return True

        title_length = max(0, int(user32.GetWindowTextLengthW(hwnd)))
        title = ctypes_module.create_unicode_buffer(title_length + 1)
        user32.GetWindowTextW(hwnd, title, len(title))
        if any(part in title.value for part in title_parts):
            matches.append(hwnd)
            return False
        return True

    user32.EnumWindows(enum_windows_proc(callback), 0)
    return matches[0] if matches else None


def _center_window(
    hwnd: int,
    user32: Any,
    ctypes_module: Any,
    wintypes_module: Any,
    center_area: tuple[int, int, int, int] | None = None,
) -> bool:
    rect = wintypes_module.RECT()
    if not user32.GetWindowRect(hwnd, ctypes_module.byref(rect)):
        return False

    work_area = wintypes_module.RECT()
    spi_get_work_area = 0x0030
    if user32.SystemParametersInfoW(spi_get_work_area, 0, ctypes_module.byref(work_area), 0):
        work_rect = (work_area.left, work_area.top, work_area.right, work_area.bottom)
    else:
        work_rect = (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

    target_rect = center_area or work_rect
    x, y = _center_rect_in_work_area(
        (rect.left, rect.top, rect.right, rect.bottom),
        target_rect,
    )
    window_width = max(1, rect.right - rect.left)
    window_height = max(1, rect.bottom - rect.top)
    work_left, work_top, work_right, work_bottom = work_rect
    x = min(max(x, work_left), max(work_left, work_right - window_width))
    y = min(max(y, work_top), max(work_top, work_bottom - window_height))

    swp_nosize = 0x0001
    swp_nozorder = 0x0004
    swp_noactivate = 0x0010
    return bool(
        user32.SetWindowPos(
            hwnd,
            0,
            x,
            y,
            0,
            0,
            swp_nosize | swp_nozorder | swp_noactivate,
        )
    )
