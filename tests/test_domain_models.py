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


@pytest.mark.parametrize(
    ("source", "duration", "has_hires", "expected_duration", "expected_name"),
    [
        pytest.param("netease", 131, True, "2:11", "Track [Hi-Res]", id="netease"),
        pytest.param("spotify", 231, False, "3:51", "Track", id="spotify"),
        pytest.param("kuwo", 324, False, "5:24", "Track", id="kuwo"),
    ],
)
def test_song_accepts_current_api_dict(
    source: str,
    duration: int,
    has_hires: bool,
    expected_duration: str,
    expected_name: str,
) -> None:
    extra_data: dict[str, object] = {"duration": duration}
    if has_hires:
        extra_data["has_hires"] = True
    song = Song.from_api(
        {
            "id": 123,
            "url_id": "u-1",
            "pic_id": "p-1",
            "lyric_id": "l-1",
            "name": "Track",
            "artist": ["A", "B"],
            "album": "Album",
            "source": source,
            "extra_data": extra_data,
        }
    )

    assert song.id == "123"
    assert song.artist == "A, B"
    assert song.duration_text == expected_duration
    assert song.display_name == expected_name


def test_song_does_not_fall_back_to_legacy_top_level_metadata() -> None:
    song = Song.from_api(
        {
            "id": "1",
            "name": "Track",
            "duration": 125,
            "has_hires": True,
        }
    )

    assert song.duration_text == "--:--"
    assert song.display_name == "Track"


def test_song_accepts_placeholder_duration() -> None:
    song = Song.from_api({"id": "1", "name": "Track", "extra_data": {"duration": "--:--"}})

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
