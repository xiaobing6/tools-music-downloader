from __future__ import annotations

import sys
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


def test_get_static_dir_returns_existing_candidate(tmp_path: Path) -> None:
    static_dir = tmp_path / "music_downloader" / "gui" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<div id='app'></div>", encoding="utf-8")

    result = app._get_static_dir(
        module_file=tmp_path / "other" / "gui" / "app.py",
        executable=tmp_path / "music_download.exe",
    )

    assert result == str(static_dir)


def test_window_size_constants_match_designed_minimum() -> None:
    assert app.DEFAULT_WINDOW_SIZE == (1266, 1013)
    assert app.MIN_WINDOW_SIZE == (1266, 1013)


def test_run_gui_uses_default_window_size(monkeypatch, tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<div id='app'></div>", encoding="utf-8")

    captured: dict[str, object] = {}

    class FakeApi:
        def set_window(self, window: FakeWindow) -> None:
            captured["window"] = window

        def shutdown(self) -> None:
            captured["shutdown"] = True

    fake_webview = ModuleType("webview")

    def create_window(**kwargs: object) -> FakeWindow:
        captured.update(kwargs)
        return FakeWindow()

    fake_webview.create_window = create_window  # type: ignore[attr-defined]
    fake_webview.start = lambda debug=False: captured.setdefault("debug", debug)  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(app, "_get_static_dir", lambda: str(static_dir))
    monkeypatch.setattr("music_downloader.gui.api.MusicApi", FakeApi)
    monkeypatch.setattr(
        "music_downloader.gui.settings.load_config",
        lambda: {
            "window_width": 1266,
            "window_height": 1013,
        },
    )

    app.run_gui()

    assert captured["width"] == 1266
    assert captured["height"] == 1013
    assert captured["min_size"] == (1266, 1013)


def test_run_gui_clamps_window_size_to_minimum(monkeypatch, tmp_path: Path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<div id='app'></div>", encoding="utf-8")

    captured: dict[str, object] = {}

    class FakeApi:
        def set_window(self, window: FakeWindow) -> None:
            captured["window"] = window

    fake_webview = ModuleType("webview")

    def create_window(**kwargs: object) -> FakeWindow:
        captured.update(kwargs)
        return FakeWindow()

    fake_webview.create_window = create_window  # type: ignore[attr-defined]
    fake_webview.start = lambda debug=False: captured.setdefault("debug", debug)  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "webview", fake_webview)
    monkeypatch.setattr(app, "_get_static_dir", lambda: str(static_dir))
    monkeypatch.setattr("music_downloader.gui.api.MusicApi", FakeApi)
    monkeypatch.setattr(
        "music_downloader.gui.settings.load_config",
        lambda: {
            "window_width": 960,
            "window_height": 680,
        },
    )

    app.run_gui()

    assert captured["width"] == 1266
    assert captured["height"] == 1013
    assert captured["min_size"] == (1266, 1013)
