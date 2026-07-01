"""Warning-oriented metadata writing adapter."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from music_downloader.domain.enums import Bitrate
from music_downloader.domain.models import Song
from music_downloader.infrastructure.tags import embed_metadata

EmbedFunc = Callable[..., None]


class MetadataWriter:
    def __init__(self, embed_func: EmbedFunc = embed_metadata):
        self._embed_func = embed_func

    def write(
        self,
        *,
        filepath: str | Path,
        song: Song,
        index: int,
        total: int,
        cover_data: bytes,
        cover_mime: str,
        lyric_text: str,
        bitrate: Bitrate | str,
    ) -> list[str]:
        try:
            self._embed_func(
                filepath=str(filepath),
                song=song.to_legacy_dict(),
                index=index,
                total=total,
                cover_data=cover_data,
                cover_mime=cover_mime,
                lyric_text=lyric_text,
                bitrate=bitrate.value if isinstance(bitrate, Bitrate) else str(bitrate),
            )
        except Exception as exc:  # noqa: BLE001 - metadata is best-effort
            return [f"写入元数据失败: {exc}"]
        return []
