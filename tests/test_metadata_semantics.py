from __future__ import annotations

from pathlib import Path
from typing import Any

from music_downloader.domain.enums import Bitrate, DownloadStatus
from music_downloader.domain.models import DownloadResult, Song
from music_downloader.infrastructure.metadata import MetadataWriter


def test_metadata_writer_returns_warning_when_embed_raises(tmp_path: Path) -> None:
    path = tmp_path / "song.mp3"
    path.write_bytes(b"audio")

    def broken_embed(**_: Any) -> None:
        raise RuntimeError("bad tag")

    writer = MetadataWriter(embed_func=broken_embed)
    warnings = writer.write(
        filepath=path,
        song=Song(id="1", name="Song"),
        index=1,
        total=1,
        cover_data=b"",
        cover_mime="image/jpeg",
        lyric_text="",
        bitrate=Bitrate.MP3_320,
    )

    assert warnings == ["写入元数据失败: bad tag"]
    assert path.exists()


def test_download_result_success_can_include_metadata_warning() -> None:
    result = DownloadResult(
        song=Song(id="1", name="Song"),
        status=DownloadStatus.SUCCESS,
        path="song.mp3",
        warnings=["写入元数据失败: bad tag"],
    )

    assert result.ok is True
