from music_downloader.gui.api import MusicApi


class FakeWindow:
    def __init__(self) -> None:
        self.scripts: list[str] = []

    def evaluate_js(self, script: str) -> None:
        self.scripts.append(script)


def test_gui_api_emits_cover_event() -> None:
    api = MusicApi()
    window = FakeWindow()
    api.set_window(window)

    api._handle_cover({"id": "1", "source": "netease", "cover": "https://covers.example/1.jpg"})

    assert "py-cover" in window.scripts[-1]
    assert '"id": "1"' in window.scripts[-1]
    assert '"cover": "https://covers.example/1.jpg"' in window.scripts[-1]
