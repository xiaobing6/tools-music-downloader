from __future__ import annotations

import sys
from types import ModuleType

from music_downloader.gui.api import MusicApi
from music_downloader.gui.settings import DEFAULT_CONFIG, load_config, save_config


class _FailingBridge:
    def search(self, *_args: object, **_kwargs: object) -> list[dict[str, object]]:
        raise AssertionError("invalid search options should not reach the bridge")

    def start_download(self, *_args: object, **_kwargs: object) -> str:
        raise AssertionError("invalid download options should not reach the bridge")


def test_load_config_returns_defaults_each_time() -> None:
    config = load_config()

    assert config["source"] == DEFAULT_CONFIG["source"]
    assert config["number"] == DEFAULT_CONFIG["number"]
    assert config["output_dir"].endswith("downloads")


def test_save_config_does_not_persist_user_choices() -> None:
    save_config({"source": "spotify", "number": 5})
    config = load_config()

    assert config["source"] == DEFAULT_CONFIG["source"]
    assert config["number"] == DEFAULT_CONFIG["number"]


def test_gui_search_rejects_invalid_options_before_bridge() -> None:
    api = MusicApi()
    api._bridge = _FailingBridge()  # type: ignore[assignment]

    assert api.search("Beyond", "invalid", "song", 20) == []


def test_gui_download_rejects_invalid_options_before_bridge() -> None:
    api = MusicApi()
    api._bridge = _FailingBridge()  # type: ignore[assignment]

    assert api.start_download([], "netease", "invalid", True, True, "downloads") == ""


def test_select_directory_uses_pywebview_folder_dialog(monkeypatch) -> None:
    fake_webview = ModuleType("webview")
    fake_tkinter = ModuleType("tkinter")

    class FakeFileDialog:
        FOLDER = 20

    class FakeWindow:
        def __init__(self) -> None:
            self.calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        def create_file_dialog(self, *args: object, **kwargs: object) -> tuple[str]:
            self.calls.append((args, kwargs))
            return (r"C:\Music",)

    def failing_tk() -> object:
        raise AssertionError("select_directory should use pywebview before tkinter")

    fake_webview.FileDialog = FakeFileDialog  # type: ignore[attr-defined]
    fake_tkinter.Tk = failing_tk  # type: ignore[attr-defined]
    fake_tkinter.filedialog = object()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setitem(sys.modules, "tkinter", fake_tkinter)

    api = MusicApi()
    window = FakeWindow()
    api.set_window(window)

    assert api.select_directory() == r"C:\Music"
    args, kwargs = window.calls[0]
    dialog_type = kwargs.get("dialog_type", args[0] if args else None)
    assert dialog_type == FakeFileDialog.FOLDER
