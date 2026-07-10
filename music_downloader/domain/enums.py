"""Domain enumerations shared by CLI, GUI, and services."""

from __future__ import annotations

from enum import Enum


class Source(str, Enum):  # noqa: UP042 - preserve legacy string formatting
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
