from __future__ import annotations

from pathlib import Path

from music_downloader.domain.enums import Bitrate
from music_downloader.domain.models import Song
from music_downloader.infrastructure.files import (
    build_output_path,
    default_download_root,
    normalize_song_dict,
    output_exists,
    safe_filename,
)


def test_default_download_root_is_project_downloads() -> None:
    root = default_download_root()

    assert root.name == "downloads"
    assert (root.parent / "music_download.py").exists()


def test_build_output_path_matches_existing_filename_rule(tmp_path: Path) -> None:
    song = Song(id="42", name="Song:Name", artist="Artist", album="Album")

    path = build_output_path(tmp_path, song, Bitrate.MP3_320)

    assert path.name == "[42] Artist - Song_Name.mp3"


def test_flac_extension(tmp_path: Path) -> None:
    song = Song(id="42", name="Song", artist="Artist")

    path = build_output_path(tmp_path, song, Bitrate.FLAC)

    assert path.suffix == ".flac"


def test_output_exists_uses_final_path_only(tmp_path: Path) -> None:
    song = Song(id="42", name="Song", artist="Artist")
    path = build_output_path(tmp_path, song, Bitrate.MP3_320)
    path.write_bytes(b"already here")

    assert output_exists(path) is True


def test_normalize_song_dict_keeps_legacy_display_shape() -> None:
    data = normalize_song_dict({"id": "1", "name": "Song", "artist": ["A"], "duration": 61})

    assert data["name"] == "Song"
    assert data["artist"] == "A"
    assert data["duration"] == "1:01"


def test_safe_filename_handles_windows_reserved_name() -> None:
    assert safe_filename("CON.mp3") == "_CON.mp3"
