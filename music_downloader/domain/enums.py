"""Domain enumerations shared by CLI, GUI, and services."""

from __future__ import annotations

from enum import StrEnum


class Source(StrEnum):
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


class SearchType(StrEnum):
    SONG = "song"
    ALBUM = "album"
    PLAYLIST = "playlist"


class Bitrate(StrEnum):
    MP3_128 = "128"
    MP3_192 = "192"
    MP3_320 = "320"
    FLAC = "flac"


class DownloadStatus(StrEnum):
    SUCCESS = "success"
    SKIP = "skip"
    FAIL = "fail"
