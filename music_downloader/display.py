import json

from .utils import normalize_song


def display_width(text):
    width = 0
    for char in text:
        if "\u4e00" <= char <= "\u9fff" or "\u3000" <= char <= "\u303f" or "\uff00" <= char <= "\uffef":
            width += 2
        else:
            width += 1
    return width


def pad_cell(text, width):
    return text + " " * (width - display_width(text))


def display_table(data, keyword):
    songs = [normalize_song(song) for song in data]
    headers = ["#", "歌名", "歌手", "专辑", "时长", "来源", "ID"]
    rows = []
    for index, song in enumerate(songs, 1):
        rows.append(
            [
                str(index),
                song["name"],
                song["artist"],
                song["album"],
                song["duration"],
                song["source"],
                song["id"],
            ]
        )

    col_widths = [display_width(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            col_widths[index] = max(col_widths[index], display_width(cell))

    sep = "+" + "+".join("-" * (width + 2) for width in col_widths) + "+"
    header_line = "|" + "|".join(
        " " + pad_cell(header, col_widths[index]) + " "
        for index, header in enumerate(headers)
    ) + "|"

    print(sep)
    print(header_line)
    print(sep)
    for row in rows:
        line = "|" + "|".join(
            " " + pad_cell(cell, col_widths[index]) + " "
            for index, cell in enumerate(row)
        ) + "|"
        print(line)
    print(sep)
    print(f'共 {len(data)} 首歌曲 (关键词: "{keyword}")')


def display_list(data, keyword):
    print("=" * 70)
    for index, song in enumerate(data, 1):
        normalized = normalize_song(song)
        print("  {:2d}. {}".format(index, normalized["name"]))
        print(
            "      歌手: {} | 专辑: {} | 时长: {} | 来源: {} | ID: {}".format(
                normalized["artist"],
                normalized["album"],
                normalized["duration"],
                normalized["source"],
                normalized["id"],
            )
        )
        print()
    print(f'共找到 {len(data)} 首歌曲 (关键词: "{keyword}")')
    print("=" * 70)


def display_results(data, keyword, output_format="table"):
    if output_format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_format == "list":
        display_list(data, keyword)
    else:
        display_table(data, keyword)
