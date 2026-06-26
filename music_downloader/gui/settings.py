"""User settings persistence for the GUI.

Settings are stored as JSON in the user's home directory:
~/.music_downloader_config.json
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_FILENAME = ".music_downloader_config.json"


def _get_config_path() -> Path:
    return Path.home() / CONFIG_FILENAME


def _get_default_output_dir() -> str:
    """Default download dir mirrors CLI default: <project_root>/downloads."""
    try:
        base_dir = Path(__file__).resolve().parent.parent.parent
    except Exception:
        base_dir = Path.cwd()
    return str(base_dir / "downloads")


DEFAULT_CONFIG: dict[str, Any] = {
    "source": "netease",
    "search_type": "song",
    "bitrate": "320",
    "number": 20,
    "output_dir": _get_default_output_dir(),
    "download_cover": True,
    "download_lyric": True,
    "window_width": 960,
    "window_height": 680,
}


def load_config() -> dict[str, Any]:
    """Load config from disk, merging with defaults for missing keys."""
    path = _get_config_path()
    config = dict(DEFAULT_CONFIG)
    config["output_dir"] = _get_default_output_dir()
    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                config.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    if not config.get("output_dir"):
        config["output_dir"] = _get_default_output_dir()
    return config


def save_config(config: dict[str, Any]) -> None:
    """Save config to disk, preserving only known keys."""
    path = _get_config_path()
    to_save = {k: config.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
