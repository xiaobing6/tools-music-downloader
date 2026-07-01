from __future__ import annotations

from typing import Any

from music_downloader.domain.enums import SearchType, Source
from music_downloader.domain.models import SearchOptions
from music_downloader.services.search import SearchService


class FakeClient:
    def search(self, options: SearchOptions) -> list[dict[str, Any]]:
        assert options.search_type == SearchType.SONG
        return [
            {"id": "1", "name": "One", "artist": "A", "source": "netease"},
            {"id": "1", "name": "One Duplicate", "artist": "A", "source": "netease"},
            {"id": "2", "name": "Two", "artist": ["B"], "source": "netease"},
        ]


def test_search_service_deduplicates_by_id() -> None:
    service = SearchService(FakeClient())

    songs = service.search(SearchOptions(keyword="x", source=Source.NETEASE, number=10))

    assert [song.id for song in songs] == ["1", "2"]
    assert songs[1].artist == "B"
