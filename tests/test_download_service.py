from __future__ import annotations

from pathlib import Path

from music_downloader.domain.enums import Bitrate, DownloadStatus, Source
from music_downloader.domain.models import DownloadOptions, Song
from music_downloader.services.download import DownloadService


class FakeClient:
    def __init__(self, play_url: str = "http://example.test/audio.mp3"):
        self.play_url = play_url

    def get_play_url(self, song: Song, source: Source | str, bitrate: Bitrate | str) -> str:
        return self.play_url

    def get_lyric(self, song: Song, source: Source | str) -> str:
        return "lyric"

    def get_pic_url(self, song: Song, source: Source | str) -> str:
        return ""


class FakeFileDownloader:
    def download(self, url: str, path: Path) -> int:
        path.write_bytes(b"x" * 20000)
        return path.stat().st_size


class BrokenMetadata:
    def write(self, **kwargs: object) -> list[str]:
        return ["写入元数据失败: bad tag"]


def test_existing_file_is_skip(tmp_path: Path) -> None:
    song = Song(id="1", name="Song", artist="A")
    existing = tmp_path / "[1] A - Song.mp3"
    existing.write_bytes(b"exists")
    service = DownloadService(FakeClient(), FakeFileDownloader(), BrokenMetadata())

    result = service.download_one(
        song,
        DownloadOptions(output_dir=tmp_path, source=Source.NETEASE, bitrate=Bitrate.MP3_320),
        index=1,
        total=1,
    )

    assert result.status == DownloadStatus.SKIP
    assert result.path == str(existing)


def test_metadata_warning_still_success(tmp_path: Path) -> None:
    song = Song(id="1", name="Song", artist="A")
    service = DownloadService(FakeClient(), FakeFileDownloader(), BrokenMetadata())

    result = service.download_one(
        song,
        DownloadOptions(output_dir=tmp_path, source=Source.NETEASE, bitrate=Bitrate.MP3_320),
        index=1,
        total=1,
    )

    assert result.status == DownloadStatus.SUCCESS
    assert result.warnings == ["写入元数据失败: bad tag"]
    assert Path(result.path).exists()


def test_missing_play_url_fails_without_creating_file(tmp_path: Path) -> None:
    song = Song(id="1", name="Song", artist="A")
    service = DownloadService(FakeClient(play_url=""), FakeFileDownloader(), BrokenMetadata())

    result = service.download_one(
        song,
        DownloadOptions(output_dir=tmp_path, source=Source.NETEASE, bitrate=Bitrate.MP3_320),
        index=1,
        total=1,
    )

    assert result.status == DownloadStatus.FAIL
    assert result.reason == "未获取到播放链接"
