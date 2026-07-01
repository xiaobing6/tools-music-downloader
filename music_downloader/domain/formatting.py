"""Pure formatting helpers shared by domain models and renderers."""

from __future__ import annotations

from typing import Any


def format_duration(seconds: int | float | None) -> str:
    """Format seconds as m:ss, returning --:-- for invalid durations."""
    if not seconds or seconds <= 0:
        return "--:--"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def get_artist_str(song: dict[str, Any]) -> str:
    """Extract an artist string from API data."""
    artist = song.get("artist", "未知")
    if isinstance(artist, list):
        return ", ".join(str(item) for item in artist)
    return str(artist)
