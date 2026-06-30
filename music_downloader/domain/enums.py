"""Domain enumerations shared by CLI, GUI, and services."""

from __future__ import annotations

from enum import Enum


class Source(str, Enum):
    NETEASE = "netease"
    MIGU = "migu"
    KUWO = "kuwo"
    YTMUSIC = "ytmusic"
    TIDAL = "tidal"
    QOBUZ = "qobuz"
    DEEZER = "deezer"
    SPOTIFY = "spotify"
    TENCENT = "tencent"
    XIMALAYA = "ximalaya"
    JOOX = "joox"
    APPLE = "apple"


class SearchType(str, Enum):
    SONG = "song"
    ALBUM = "album"
    PLAYLIST = "playlist"


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    LIST = "list"


class Bitrate(str, Enum):
    MP3_128 = "128"
    MP3_192 = "192"
    MP3_320 = "320"
    FLAC = "flac"


class DownloadStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    SKIP = "skip"
    FAIL = "fail"
    CANCELLED = "cancelled"
