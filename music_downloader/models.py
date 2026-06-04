from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunOptions:
    keyword: str
    source: str
    search_type: str
    number: int
    output_dir: str
    output_format: str
    search_only: bool
    select: bool
    download_lyric: bool
    download_cover: bool
    bitrate: str
    version: str
