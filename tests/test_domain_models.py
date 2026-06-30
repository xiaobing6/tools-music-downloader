from __future__ import annotations

import pytest
from pydantic import ValidationError

from music_downloader.domain.enums import Bitrate, DownloadStatus, SearchType, Source
from music_downloader.domain.models import DownloadResult, SearchOptions, Song


def test_song_accepts_legacy_api_dict() -> None:
    song = Song.from_api(
        {
            "id": 123,
            "url_id": "u-1",
            "pic_id": "p-1",
            "lyric_id": "l-1",
            "name": "Track",
            "artist": ["A", "B"],
            "album": "Album",
            "duration": 125,
            "source": "netease",
            "has_hires": True,
        }
    )

    assert song.id == "123"
    assert song.artist == "A, B"
    assert song.display_name == "Track [Hi-Res]"
    assert song.duration_text == "2:05"


def test_search_options_validate_values() -> None:
    options = SearchOptions(keyword="Beyond", source=Source.NETEASE, search_type=SearchType.SONG)

    assert options.keyword == "Beyond"
    assert options.source == Source.NETEASE


def test_search_options_reject_invalid_number() -> None:
    with pytest.raises(ValidationError):
        SearchOptions(keyword="Beyond", number=0)


def test_download_result_records_warning_success() -> None:
    result = DownloadResult(
        song=Song(id="1", name="Song"),
        status=DownloadStatus.SUCCESS,
        path="downloads/Song.mp3",
        warnings=["ID3 标签写入失败"],
    )

    assert result.ok is True
    assert result.warnings == ["ID3 标签写入失败"]


def test_bitrate_values_match_cli() -> None:
    assert [item.value for item in Bitrate] == ["128", "192", "320", "flac"]
