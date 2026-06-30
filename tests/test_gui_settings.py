from __future__ import annotations

from pathlib import Path

from music_downloader.gui import settings
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


def test_save_config_does_not_persist_user_choices(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "_get_config_path", lambda: tmp_path / "config.json")

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
