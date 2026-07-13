"""Default-only GUI settings.

GUI choices are intentionally not persisted between runs.
"""

from __future__ import annotations

import sys
from typing import Any

from music_downloader.core.runtime import runtime_root


def _get_default_output_dir() -> str:
    """Default download dir mirrors CLI default: <project_root>/downloads.

    Uses the same source/executable root logic as the CLI so GUI and CLI defaults stay
    in sync whether running from source or a Nuitka-compiled executable.
    """
    base_dir = runtime_root(
        __file__,
        compiled="__compiled__" in globals(),
        executable=sys.argv[0],
    )
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
