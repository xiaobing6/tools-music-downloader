import json
from typing import Any, Dict, List

from rich.table import Table

from .console import console
from .utils import normalize_song


def display_table(data: List[Dict[str, Any]], keyword: str) -> None:
    songs = [normalize_song(song) for song in data]
    table = Table(title=f'搜索结果："{keyword}"')
    for header in ["#", "歌名", "歌手", "专辑", "时长", "来源", "ID"]:
        table.add_column(header)

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


def display_list(data: List[Dict[str, Any]], keyword: str) -> None:
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


def display_results(data: List[Dict[str, Any]], keyword: str, output_format: str = "table") -> None:
    if output_format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_format == "list":
        display_list(data, keyword)
    else:
        display_table(data, keyword)
