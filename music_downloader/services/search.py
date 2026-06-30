"""Shared search workflow."""

from __future__ import annotations

from typing import Any, Protocol

from music_downloader.domain.models import SearchOptions, Song


class SearchClient(Protocol):
    def search(self, options: SearchOptions) -> list[dict[str, Any]]:
        ...


class SearchService:
    def __init__(self, client: SearchClient):
        self._client = client

    def search(self, options: SearchOptions) -> list[Song]:
        raw_results = self._client.search(options)
        seen: set[str] = set()
        songs: list[Song] = []
        for item in raw_results:
            song = Song.from_api(item)
            if song.id and song.id in seen:
                continue
            if song.id:
                seen.add(song.id)
            songs.append(song)
        return songs[: options.number]
