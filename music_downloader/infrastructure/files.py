"""Shared file naming and output path rules."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from music_downloader.domain.enums import Bitrate
from music_downloader.domain.models import Song
from music_downloader.utils import format_duration, get_artist_str

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


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_download_root() -> Path:
    return project_root() / "downloads"


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


def output_extension(bitrate: Bitrate | str) -> str:
    value = bitrate.value if isinstance(bitrate, Bitrate) else str(bitrate)
    return ".flac" if value == Bitrate.FLAC.value else ".mp3"


def build_output_path(root: str | os.PathLike[str], song: Song, bitrate: Bitrate | str) -> Path:
    filename = safe_filename(
        f"[{song.id}] {song.artist} - {song.name}{output_extension(bitrate)}"
    )
    return Path(root) / filename


def output_exists(path: str | os.PathLike[str]) -> bool:
    return Path(path).exists()


def ensure_directory(path: str | os.PathLike[str]) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def normalize_song_dict(song: dict[str, Any]) -> dict[str, str]:
    model = Song.from_api(song)
    return {
        "name": model.display_name,
        "artist": get_artist_str(song),
        "album": str(song.get("album", "未知")),
        "duration": format_duration(song.get("duration", 0)),
        "source": str(song.get("source", "未知")),
        "id": model.id,
        "url_id": model.url_id,
        "pic_id": model.pic_id,
        "lyric_id": model.lyric_id,
    }
