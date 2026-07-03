"""Default-only GUI settings.

GUI choices are intentionally not persisted between runs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

CONFIG_FILENAME = ".music_downloader_config.json"


def _get_config_path() -> Path:
    return Path.home() / CONFIG_FILENAME


def _get_default_output_dir() -> str:
    """Default download dir mirrors CLI default: <project_root>/downloads.

    Uses the same resolution logic as cli.py so the GUI and CLI defaults stay
    in sync whether running from source or a Nuitka-compiled executable.
    """
    if "__compiled__" in globals():
        base_dir = Path(os.path.dirname(os.path.abspath(sys.argv[0])))
    else:
        # __file__ is music_downloader/gui/settings.py; go up to project root.
        base_dir = Path(__file__).resolve().parent.parent.parent
    return str(base_dir / "downloads")


DEFAULT_CONFIG: dict[str, Any] = {
    "source": "netease",
    "search_type": "song",
    "bitrate": "320",
    "number": 20,
    "output_dir": _get_default_output_dir(),
    "download_cover": True,
    "download_lyric": True,
    "window_width": 1280,
    "window_height": 800,
}


def load_config() -> dict[str, Any]:
    """Return a fresh default config for every GUI launch."""
    config = dict(DEFAULT_CONFIG)
    config["output_dir"] = _get_default_output_dir()
    return config


def save_config(config: dict[str, Any]) -> None:
    """No-op: GUI settings reset to defaults on next launch."""
    return None
