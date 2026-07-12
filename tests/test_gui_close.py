from __future__ import annotations

import threading

from music_downloader.gui.api import MusicApi


class FakeWindow:
    def __init__(self) -> None:
        self.scripts: list[str] = []
        self.destroyed = False
        self.destroyed_event = threading.Event()

    def evaluate_js(self, script: str) -> None:
        self.scripts.append(script)

    def destroy(self) -> None:
        self.destroyed = True
        self.destroyed_event.set()


def test_close_confirmation_emits_request_and_allows_one_confirmed_close() -> None:
    api = MusicApi()
    window = FakeWindow()
    api.set_window(window)

    api.request_close_confirmation()
    assert any("py-close-request" in script for script in window.scripts)
    assert api.consume_close_confirmation() is False

    api.confirm_close()
    assert window.destroyed is False
    assert window.destroyed_event.wait(timeout=1)
    assert api.consume_close_confirmation() is True
    assert api.consume_close_confirmation() is False
