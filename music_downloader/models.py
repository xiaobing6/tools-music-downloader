from __future__ import annotations

from dataclasses import dataclass


# NOTE: 字段变更时需同步更新 cli.make_run_options 与 cli.build_interactive_options。
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
