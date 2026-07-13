from __future__ import annotations

from pathlib import Path

from music_downloader.domain.models import Song
from music_downloader.infrastructure.downloader import build_output_path
from music_downloader.infrastructure.files import normalize_song_dict, safe_filename


def test_build_output_path_matches_existing_filename_rule(tmp_path: Path) -> None:
    song = {"id": "42", "name": "Song:Name", "artist": "Artist", "album": "Album"}

    path = Path(build_output_path(str(tmp_path), song, "320"))

    assert path.name == "[42] Artist - Song_Name.mp3"


def test_flac_extension(tmp_path: Path) -> None:
    song = {"id": "42", "name": "Song", "artist": "Artist"}

    path = Path(build_output_path(str(tmp_path), song, "flac"))

    assert path.suffix == ".flac"


def test_normalize_song_dict_keeps_display_shape() -> None:
    song = Song.from_api(
        {
            "id": "1",
            "name": "Song",
            "artist": ["A"],
            "extra_data": {"duration": 61},
        }
    )

    data = normalize_song_dict(song.to_result_dict())

    assert data["name"] == "Song"
    assert data["artist"] == "A"
    assert data["duration"] == "1:01"


def test_normalize_song_dict_handles_placeholder_duration() -> None:
    data = normalize_song_dict({"id": "1", "name": "Song", "artist": ["A"], "duration": "--:--"})

    assert data["duration"] == "--:--"


def test_normalize_song_dict_uses_source_catalog_display_name() -> None:
    data = normalize_song_dict({"id": "1", "name": "Song", "artist": ["A"], "source": "netease"})

    assert data["source"] == "网易云音乐"


def test_safe_filename_handles_windows_reserved_name() -> None:
    assert safe_filename("CON.mp3") == "_CON.mp3"
