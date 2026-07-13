"""Domain enumerations shared by CLI, GUI, and services."""

from __future__ import annotations

from enum import Enum


class Source(str, Enum):  # noqa: UP042 - preserve legacy string formatting
    label: str

    def __new__(cls, value: str, label: str = "") -> Source:
        member = str.__new__(cls, value)
        member._value_ = value
        member.label = label
        return member

    NETEASE = ("netease", "网易云音乐")
    MIGU = ("migu", "咪咕音乐")
    KUGOU = ("kugou", "酷狗音乐")
    KUWO = ("kuwo", "酷我音乐")
    YTMUSIC = ("ytmusic", "YouTube Music")
    TIDAL = ("tidal", "Tidal")
    QOBUZ = ("qobuz", "Qobuz")
    DEEZER = ("deezer", "Deezer")
    SPOTIFY = ("spotify", "Spotify")
    TENCENT = ("tencent", "QQ音乐")
    XIMALAYA = ("ximalaya", "喜马拉雅")
    JOOX = ("joox", "JOOX")
    APPLE = ("apple", "Apple Music")


def source_label(value: object, fallback: str = "未知") -> str:
    """Return a catalog label while preserving unknown upstream source IDs."""
    text = str(value).strip() if value is not None else ""
    if not text:
        return fallback
    try:
        return Source(text).label
    except ValueError:
        return text


class SearchType(str, Enum):  # noqa: UP042 - preserve legacy string formatting
    SONG = "song"
    ALBUM = "album"
    PLAYLIST = "playlist"


class Bitrate(str, Enum):  # noqa: UP042 - preserve legacy string formatting
    MP3_128 = "128"
    MP3_192 = "192"
    MP3_320 = "320"
    FLAC = "flac"


class DownloadStatus(str, Enum):  # noqa: UP042 - preserve legacy string formatting
    SUCCESS = "success"
    SKIP = "skip"
    FAIL = "fail"
