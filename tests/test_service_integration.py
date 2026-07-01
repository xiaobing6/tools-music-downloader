from __future__ import annotations

from pathlib import Path
from typing import Any

from music_downloader.domain.enums import Bitrate, DownloadStatus, Source
from music_downloader.domain.models import DownloadOptions, SearchOptions, Song
from music_downloader.services.download import DownloadService
from music_downloader.services.search import SearchService


class FakeClient:
    def search(self, options: SearchOptions) -> list[dict[str, Any]]:
        return [{"id": "1", "name": options.keyword, "artist": "A", "source": options.source.value}]

    def get_play_url(self, song: Song, source: Source | str, bitrate: Bitrate | str) -> str:
        return "http://example.test/audio.mp3"

    def get_lyric(self, song: Song, source: Source | str) -> str:
        return ""

    def get_pic_url(self, song: Song, source: Source | str) -> str:
        return ""


class FakeFileDownloader:
    def download(self, url: str, path: Path) -> int:
        path.write_bytes(b"x" * 20000)
        return path.stat().st_size


class NoopMetadata:
    def write(self, **kwargs: object) -> list[str]:
        return []


def test_search_then_download_shared_workflow(tmp_path: Path) -> None:
    client = FakeClient()
    songs = SearchService(client).search(SearchOptions(keyword="Song"))
    result = DownloadService(client, FakeFileDownloader(), NoopMetadata()).download_one(
        songs[0],
        DownloadOptions(output_dir=tmp_path, source=Source.NETEASE, bitrate=Bitrate.MP3_320),
        index=1,
        total=1,
    )

    assert result.status == DownloadStatus.SUCCESS
    assert Path(result.path).exists()
