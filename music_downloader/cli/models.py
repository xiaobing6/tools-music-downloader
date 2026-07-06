"""运行选项数据类。"""

from __future__ import annotations

from dataclasses import dataclass


# NOTE: 字段变更时需同步更新 cli.app._build_run_options 与 cli.build_interactive_options。
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
    interactive: bool = False
    user_data_dir: str | None = None
