from __future__ import annotations

import pytest
from pydantic import ValidationError

from music_downloader.core.config import (
    DEFAULT_BITRATE,
    DEFAULT_SOURCE,
    SEARCH_TYPE_MAP,
    VALID_BITRATES,
    VALID_SOURCES,
)
from music_downloader.domain.enums import Bitrate, DownloadStatus, SearchType, Source
from music_downloader.domain.models import SearchOptions, Song


def test_song_accepts_api_dict() -> None:
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


def test_song_accepts_placeholder_duration() -> None:
    song = Song.from_api({"id": "1", "name": "Track", "duration": "--:--"})

    assert song.duration is None
    assert song.duration_text == "--:--"


def test_search_options_validate_values() -> None:
    options = SearchOptions(keyword="Beyond", source=Source.NETEASE, search_type=SearchType.SONG)

    assert options.keyword == "Beyond"
    assert options.source == Source.NETEASE


def test_search_options_reject_invalid_number() -> None:
    with pytest.raises(ValidationError):
        SearchOptions(keyword="Beyond", number=0)


def test_bitrate_values_match_cli() -> None:
    assert [item.value for item in Bitrate] == ["128", "192", "320", "flac"]


def test_config_choices_match_domain_enums() -> None:
    assert [item.value for item in Source] == VALID_SOURCES
    assert [item.value for item in Bitrate] == VALID_BITRATES
    assert list(SEARCH_TYPE_MAP) == [item.value for item in SearchType]
    assert DEFAULT_SOURCE in VALID_SOURCES
    assert DEFAULT_BITRATE in VALID_BITRATES


@pytest.mark.parametrize(
    ("member", "expected"),
    [
        pytest.param(Source.NETEASE, "Source.NETEASE", id="source"),
        pytest.param(SearchType.SONG, "SearchType.SONG", id="search-type"),
        pytest.param(Bitrate.MP3_320, "Bitrate.MP3_320", id="bitrate"),
        pytest.param(DownloadStatus.SUCCESS, "DownloadStatus.SUCCESS", id="download-status"),
    ],
)
def test_string_domain_enums_preserve_legacy_formatting(member: object, expected: str) -> None:
    assert str(member) == expected
    assert f"{member}" == expected
    assert format(member) == expected
