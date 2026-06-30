"""Shared download workflow for CLI and GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from music_downloader.domain.enums import Bitrate, DownloadStatus, Source
from music_downloader.domain.models import DownloadOptions, DownloadResult, Song
from music_downloader.infrastructure.files import build_output_path, ensure_directory, output_exists


class DownloadClient(Protocol):
    def get_play_url(self, song: Song, source: Source | str, bitrate: Bitrate | str) -> str:
        ...

    def get_lyric(self, song: Song, source: Source | str) -> str:
        ...

    def get_pic_url(self, song: Song, source: Source | str) -> str:
        ...


class FileDownloader(Protocol):
    def download(self, url: str, path: Path) -> int:
        ...


class MetadataWriterProtocol(Protocol):
    def write(self, **kwargs: Any) -> list[str]:
        ...


class DownloadService:
    def __init__(
        self,
        client: DownloadClient,
        file_downloader: FileDownloader,
        metadata_writer: MetadataWriterProtocol,
    ):
        self._client = client
        self._file_downloader = file_downloader
        self._metadata_writer = metadata_writer

    def download_one(
        self,
        song: Song,
        options: DownloadOptions,
        *,
        index: int,
        total: int,
    ) -> DownloadResult:
        target_dir = ensure_directory(options.output_dir)
        target_path = build_output_path(target_dir, song, options.bitrate)
        if output_exists(target_path):
            return DownloadResult(song=song, status=DownloadStatus.SKIP, path=str(target_path))

        play_url = self._client.get_play_url(song, options.source, options.bitrate)
        if not play_url:
            return DownloadResult(song=song, status=DownloadStatus.FAIL, reason="未获取到播放链接")

        try:
            size_bytes = self._file_downloader.download(play_url, target_path)
        except Exception as exc:  # noqa: BLE001 - single-song failure
            return DownloadResult(song=song, status=DownloadStatus.FAIL, reason=str(exc))

        lyric_text = self._client.get_lyric(song, options.source) if options.download_lyric else ""
        cover_data = b""
        cover_mime = "image/jpeg"
        warnings = self._metadata_writer.write(
            filepath=target_path,
            song=song,
            index=index,
            total=total,
            cover_data=cover_data,
            cover_mime=cover_mime,
            lyric_text=lyric_text,
            bitrate=options.bitrate,
        )
        return DownloadResult(
            song=song,
            status=DownloadStatus.SUCCESS,
            path=str(target_path),
            warnings=warnings,
            size_bytes=size_bytes,
        )

    def download_many(self, songs: list[Song], options: DownloadOptions) -> list[DownloadResult]:
        total = len(songs)
        return [
            self.download_one(song, options, index=index + 1, total=total)
            for index, song in enumerate(songs)
        ]
