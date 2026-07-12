from __future__ import annotations

import struct
import sys
import threading
from pathlib import Path
from types import ModuleType

from music_downloader.gui import app


class FakeEventHook:
    def __init__(self) -> None:
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


class FakeEvents:
    def __init__(self) -> None:
        self.closing = FakeEventHook()
        self.closed = FakeEventHook()


class FakeWindow:
    def __init__(self) -> None:
        self.events = FakeEvents()


def test_candidate_static_dirs_include_module_static_first(tmp_path: Path) -> None:
    module_file = tmp_path / "music_downloader" / "gui" / "app.py"
    executable = tmp_path / "dist" / "music_download.exe"

    candidates = app._candidate_static_dirs(module_file=module_file, executable=executable)

    assert candidates[0] == module_file.parent / "static"
    assert executable.parent / "music_downloader" / "gui" / "static" in candidates
    assert executable.parent / "static" in candidates


def test_candidate_icon_paths_include_source_and_bundled_locations(tmp_path: Path) -> None:
    module_file = tmp_path / "music_downloader" / "gui" / "app.py"
    executable = tmp_path / "dist" / "music_download.exe"

    candidates = app._candidate_icon_paths(module_file=module_file, executable=executable)

    assert candidates[0] == module_file.parent / "assets" / "music_downloader.ico"
    assert (
        executable.parent / "music_downloader" / "gui" / "assets" / "music_downloader.ico"
        in candidates
    )
    assert executable.parent / "assets" / "music_downloader.ico" in candidates


def test_windows_app_icon_contains_multiple_resolutions() -> None:
    icon = Path(app.__file__).resolve().parent / "assets" / "music_downloader.ico"
    data = icon.read_bytes()
    reserved, image_type, count = struct.unpack_from("<HHH", data)
    assert (reserved, image_type) == (0, 1)
    sizes = {
        (entry[0] or 256, entry[1] or 256)
        for entry in struct.iter_unpack("<BBBBHHII", data[6 : 6 + 16 * count])
    }
    assert {(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)} <= sizes


def test_get_static_dir_returns_existing_candidate(tmp_path: Path) -> None:
    static_dir = tmp_path / "music_downloader" / "gui" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<div id='app'></div>", encoding="utf-8")

    result = app._get_static_dir(
        module_file=tmp_path / "other" / "gui" / "app.py",
        executable=tmp_path / "music_download.exe",
    )

    assert result == str(static_dir)


def test_window_size_constants_match_workbench_layout() -> None:
    assert app.DEFAULT_WINDOW_SIZE == (1280, 800)
    assert app.MIN_WINDOW_SIZE == (1024, 720)


def test_run_gui_uses_default_window_size(monkeypatch, tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<div id='app'></div>", encoding="utf-8")

    captured: dict[str, object] = {}

    class FakeApi:
        def __init__(self) -> None:
            self.close_confirmed = False
            captured["api"] = self

        def set_window(self, window: FakeWindow) -> None:
            captured["window"] = window

        def consume_close_confirmation(self) -> bool:
            confirmed = self.close_confirmed
            self.close_confirmed = False
            return confirmed

        def request_close_confirmation(self) -> None:
            captured["close_request_thread"] = threading.get_ident()
            captured["close_requests"] = int(captured.get("close_requests", 0)) + 1
            close_request_sent.set()

        def shutdown(self) -> None:
            captured["shutdown"] = True

    close_request_sent = threading.Event()
    fake_webview = ModuleType("webview")

    def create_window(**kwargs: object) -> FakeWindow:
        captured.update(kwargs)
        return FakeWindow()

    fake_webview.create_window = create_window  # type: ignore[attr-defined]

    def start(*, debug: bool = False, icon: str | None = None) -> None:
        captured["debug"] = debug
        captured["icon"] = icon

    fake_webview.start = start  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(app, "_get_static_dir", lambda: str(static_dir))
    monkeypatch.setattr(app, "_get_icon_path", lambda: str(tmp_path / "music_downloader.ico"))
    monkeypatch.setattr("music_downloader.gui.api.MusicApi", FakeApi)
    monkeypatch.setattr(
        "music_downloader.gui.settings.load_config",
        lambda: {
            "window_width": 1280,
            "window_height": 800,
        },
    )

    app.run_gui()

    assert captured["width"] == 1280
    assert captured["height"] == 800
    assert captured["min_size"] == (1024, 720)
    assert captured["icon"] == str(tmp_path / "music_downloader.ico")
    assert captured["confirm_close"] is False
    assert "localization" not in captured

    window = captured["window"]
    assert isinstance(window, FakeWindow)
    assert len(window.events.closing.handlers) == 1
    closing_handler = window.events.closing.handlers[0]
    closing_thread = threading.get_ident()
    assert closing_handler() is False
    assert close_request_sent.wait(timeout=1)
    assert captured["close_requests"] == 1
    assert captured["close_request_thread"] != closing_thread
    api = captured["api"]
    assert isinstance(api, FakeApi)
    api.close_confirmed = True
    assert closing_handler() is True
    assert len(window.events.closed.handlers) == 1
    window.events.closed.handlers[0]()
    assert captured["shutdown"] is True


def test_run_gui_clamps_window_size_to_minimum(monkeypatch, tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<div id='app'></div>", encoding="utf-8")

    captured: dict[str, object] = {}

    class FakeApi:
        def __init__(self) -> None:
            self.close_confirmed = False

        def set_window(self, window: FakeWindow) -> None:
            captured["window"] = window

        def consume_close_confirmation(self) -> bool:
            confirmed = self.close_confirmed
            self.close_confirmed = False
            return confirmed

        def request_close_confirmation(self) -> None:
            captured["close_requests"] = int(captured.get("close_requests", 0)) + 1

    fake_webview = ModuleType("webview")

    def create_window(**kwargs: object) -> FakeWindow:
        captured.update(kwargs)
        return FakeWindow()

    fake_webview.create_window = create_window  # type: ignore[attr-defined]

    def start(*, debug: bool = False, icon: str | None = None) -> None:
        captured["debug"] = debug
        captured["icon"] = icon

    fake_webview.start = start  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(app, "_get_static_dir", lambda: str(static_dir))
    monkeypatch.setattr(app, "_get_icon_path", lambda: str(tmp_path / "music_downloader.ico"))
    monkeypatch.setattr("music_downloader.gui.api.MusicApi", FakeApi)
    monkeypatch.setattr(
        "music_downloader.gui.settings.load_config",
        lambda: {
            "window_width": 960,
            "window_height": 680,
        },
    )

    app.run_gui()

    assert captured["width"] == 1024
    assert captured["height"] == 720
    assert captured["min_size"] == (1024, 720)
