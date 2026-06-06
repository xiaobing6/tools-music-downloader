"""搜索结果展示：表格、列表、JSON 三种输出格式。"""

import json
from typing import Any

from .console import PlainConsole, RichTable, console
from .utils import normalize_song


def display_table(data: list[dict[str, Any]], keyword: str) -> None:
    """以 rich 表格展示搜索结果，rich 不可用时回退到列表格式。"""
    if RichTable is None:
        display_list(data, keyword)
        return

    songs = [normalize_song(song) for song in data]
    table = RichTable(title=f'搜索结果："{keyword}"', show_lines=False)
    # 各列宽度上限 + 溢出策略：歌名/歌手/专辑是中文长字段，限制 + 折行
    column_specs: list = [
        ("#", {"justify": "right", "style": "cyan", "width": 4, "no_wrap": True}),
        ("歌名", {"style": "bold", "max_width": 36, "overflow": "fold"}),
        ("歌手", {"max_width": 28, "overflow": "fold"}),
        ("专辑", {"max_width": 28, "overflow": "fold"}),
        ("时长", {"justify": "right", "width": 8, "no_wrap": True}),
        ("来源", {"width": 10, "no_wrap": True}),
        ("ID", {"style": "dim", "width": 16, "no_wrap": True}),
    ]
    for header, kwargs in column_specs:
        table.add_column(header, **kwargs)

    for index, song in enumerate(songs, 1):
        table.add_row(
            str(index),
            song["name"],
            song["artist"],
            song["album"],
            song["duration"],
            song["source"],
            song["id"],
        )

    console.print(table)
    console.print(f'共 {len(data)} 首歌曲 (关键词: "{keyword}")', style="cyan")


def display_list(data: list[dict[str, Any]], keyword: str) -> None:
    """以纯文本列表展示搜索结果。"""
    # When rich is unavailable we render with PlainConsole so the output
    # goes directly to sys.stdout (and is therefore captured by
    # capsys in tests).
    sink = PlainConsole() if RichTable is None else console
    sink.rule(f'搜索结果："{keyword}"')
    for index, song in enumerate(data, 1):
        normalized = normalize_song(song)
        sink.print(f"  {index:2d}. {normalized['name']}", style="bold")
        sink.print(
            "      歌手: {artist} | 专辑: {album} | 时长: {duration} | 来源: {source} | ID: {id}".format(
                **normalized
            )
        )
        sink.print()
    sink.print(f'共找到 {len(data)} 首歌曲 (关键词: "{keyword}")', style="cyan")


def display_results(data: list[dict[str, Any]], keyword: str, output_format: str = "table") -> None:
    """根据 output_format 选择展示方式：table / list / json。"""
    if output_format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_format == "list":
        display_list(data, keyword)
    else:
        display_table(data, keyword)
