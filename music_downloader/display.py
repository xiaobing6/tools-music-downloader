import json
from typing import Any

from .console import console
from .utils import normalize_song

RichTable: Any
try:
    from rich.table import Table as RichTable
except ImportError:
    RichTable = None


def display_table(data: list[dict[str, Any]], keyword: str) -> None:
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
    console.rule(f'搜索结果："{keyword}"')
    for index, song in enumerate(data, 1):
        normalized = normalize_song(song)
        console.print(f"  {index:2d}. {normalized['name']}", style="bold")
        console.print(
            "      歌手: {artist} | 专辑: {album} | 时长: {duration} | 来源: {source} | ID: {id}".format(
                **normalized
            )
        )
        console.print()
    console.print(f'共找到 {len(data)} 首歌曲 (关键词: "{keyword}")', style="cyan")


def display_results(data: list[dict[str, Any]], keyword: str, output_format: str = "table") -> None:
    if output_format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_format == "list":
        display_list(data, keyword)
    else:
        display_table(data, keyword)
