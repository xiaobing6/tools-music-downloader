from __future__ import annotations

import sys
from types import ModuleType

from music_downloader.gui import api as api_module
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
    assert config["window_width"] == 1266
    assert config["window_height"] == 1013


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


def test_select_directory_centers_pywebview_folder_dialog_on_windows(monkeypatch) -> None:
    fake_webview = ModuleType("webview")
    events: list[object] = []

    class FakeFileDialog:
        FOLDER = 20

    class FakeWindow:
        def create_file_dialog(self, *args: object, **kwargs: object) -> tuple[str]:
            events.append(("dialog", args, kwargs))
            return (r"C:\Music",)

    fake_webview.FileDialog = FakeFileDialog  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(
        api_module,
        "_start_center_folder_dialog",
        lambda window: events.append(("center", window)),
        raising=False,
    )

    api = MusicApi()
    window = FakeWindow()
    api.set_window(window)

    assert api.select_directory() == r"C:\Music"
    assert events[0] == ("center", window)
    assert events[1][0] == "dialog"


def test_select_directory_fallback_centers_tk_dialog(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class FakeRoot:
        def withdraw(self) -> None:
            calls["withdrawn"] = True

        def attributes(self, *args: object) -> None:
            calls["attributes"] = args

        def winfo_screenwidth(self) -> int:
            return 1920

        def winfo_screenheight(self) -> int:
            return 1080

        def update_idletasks(self) -> None:
            calls["updated"] = True

        def geometry(self, value: str) -> None:
            calls["geometry"] = value

        def destroy(self) -> None:
            calls["destroyed"] = True

    root = FakeRoot()

    def fake_askdirectory(**kwargs: object) -> str:
        calls["askdirectory"] = kwargs
        return r"C:\Music"

    fake_tkinter = ModuleType("tkinter")
    fake_tkinter.Tk = lambda: root  # type: ignore[attr-defined]
    fake_tkinter.filedialog = type(  # type: ignore[attr-defined]
        "FakeFileDialog",
        (),
        {"askdirectory": staticmethod(fake_askdirectory)},
    )
    monkeypatch.setitem(sys.modules, "tkinter", fake_tkinter)

    api = MusicApi()

    assert api.select_directory() == r"C:\Music"
    assert calls["geometry"] == "1x1+959+539"
    assert calls["attributes"] == ("-topmost", True)
    assert calls["askdirectory"] == {"title": "选择下载目录", "parent": root}
    assert calls["destroyed"] is True


def test_open_download_dir_centers_explorer_on_windows(monkeypatch, tmp_path) -> None:
    target = tmp_path / "downloads"
    calls: dict[str, object] = {}

    def fake_popen(args: list[str]) -> None:
        calls["popen"] = args

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(api_module.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        api_module, "_center_explorer_window", lambda: calls.setdefault("centered", True)
    )

    api = MusicApi()
    api.open_download_dir(str(target))

    assert target.is_dir()
    assert calls["popen"] == ["explorer", str(target)]
    assert calls["centered"] is True


def test_center_rect_in_work_area() -> None:
    assert api_module._center_rect_in_work_area((0, 0, 800, 600), (0, 0, 1920, 1040)) == (
        560,
        220,
    )
    assert api_module._center_rect_in_work_area((0, 0, 2400, 1200), (10, 20, 1010, 820)) == (
        10,
        20,
    )
