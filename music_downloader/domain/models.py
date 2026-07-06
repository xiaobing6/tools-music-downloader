"""Pydantic domain models shared by CLI, GUI, and services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from music_downloader.core.config import (
    DEFAULT_BITRATE,
    DEFAULT_KEYWORD,
    DEFAULT_NUMBER,
    DEFAULT_SOURCE,
)
from music_downloader.domain.enums import Bitrate, DownloadStatus, OutputFormat, SearchType, Source
from music_downloader.domain.formatting import format_duration, get_artist_str


class Song(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str = ""
    url_id: str = ""
    pic_id: str = ""
    lyric_id: str = ""
    name: str = "未知"
    artist: str = "未知"
    album: str = "未知"
    duration: int | float | None = None
    source: str = "未知"
    has_hires: bool = False

    @field_validator("id", "url_id", "pic_id", "lyric_id", "name", "album", "source", mode="before")
    @classmethod
    def _coerce_text(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    @field_validator("artist", mode="before")
    @classmethod
    def _coerce_artist(cls, value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if value is None:
            return "未知"
        return str(value)

    @field_validator("duration", mode="before")
    @classmethod
    def _coerce_duration(cls, value: Any) -> int | float | None:
        if value is None:
            return None
        if isinstance(value, str):
            text = value.strip()
            if not text or text == "--:--":
                return None
            try:
                return int(text)
            except ValueError:
                try:
                    return float(text)
                except ValueError:
                    return None
        return value

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Song:
        return cls(
            id=data.get("id", ""),
            url_id=data.get("url_id", ""),
            pic_id=data.get("pic_id", ""),
            lyric_id=data.get("lyric_id", ""),
            name=data.get("name", "未知"),
            artist=get_artist_str(data),
            album=data.get("album", "未知"),
            duration=data.get("duration", 0),
            source=data.get("source", "未知"),
            has_hires=bool(data.get("has_hires", False)),
        )

    @property
    def display_name(self) -> str:
        return f"{self.name} [Hi-Res]" if self.has_hires else self.name

    @property
    def duration_text(self) -> str:
        return format_duration(self.duration)

    def to_result_dict(self) -> dict[str, str]:
        return {
            "name": self.display_name,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration_text,
            "source": self.source,
            "id": self.id,
            "url_id": self.url_id,
            "pic_id": self.pic_id,
            "lyric_id": self.lyric_id,
        }


class SearchOptions(BaseModel):
    keyword: str = Field(default=DEFAULT_KEYWORD, min_length=1)
    source: Source = Source(DEFAULT_SOURCE)
    search_type: SearchType = SearchType.SONG
    number: int = Field(default=DEFAULT_NUMBER, ge=1)
    output_format: OutputFormat = OutputFormat.TABLE


class DownloadOptions(BaseModel):
    source: Source = Source(DEFAULT_SOURCE)
    bitrate: Bitrate = Bitrate(DEFAULT_BITRATE)
    output_dir: Path
    group_name: str = ""
    download_lyric: bool = True
    download_cover: bool = True


class DownloadResult(BaseModel):
    song: Song
    status: DownloadStatus
    path: str = ""
    reason: str = ""
    warnings: list[str] = Field(default_factory=list)
    size_bytes: int = 0

    @property
    def ok(self) -> bool:
        return self.status in {DownloadStatus.SUCCESS, DownloadStatus.SKIP}


class AppSettings(BaseModel):
    source: Source = Source(DEFAULT_SOURCE)
    search_type: SearchType = SearchType.SONG
    bitrate: Bitrate = Bitrate(DEFAULT_BITRATE)
    number: int = Field(default=DEFAULT_NUMBER, ge=1)
    download_cover: bool = True
    download_lyric: bool = True
