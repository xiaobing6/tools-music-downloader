"""Shared file naming and output path rules."""

from __future__ import annotations

import os
import re
from typing import Any

from music_downloader.domain.formatting import get_artist_str
from music_downloader.domain.models import Song

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def safe_filename(name: str, max_length: int = 180) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "download"

    stem, ext = os.path.splitext(cleaned)
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"

    max_stem_length = max_length - len(ext)
    if len(stem) > max_stem_length:
        stem = stem[:max_stem_length].rstrip(" .")
    return f"{stem}{ext}"


def normalize_song_dict(song: dict[str, Any]) -> dict[str, str]:
    model = Song.from_api(song)
    return {
        "name": model.display_name,
        "artist": get_artist_str(song),
        "album": str(song.get("album", "未知")),
        "duration": model.duration_text,
        "source": str(song.get("source", "未知")),
        "id": model.id,
        "url_id": model.url_id,
        "pic_id": model.pic_id,
        "lyric_id": model.lyric_id,
    }
