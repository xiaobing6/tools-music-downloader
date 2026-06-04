import os
import re
import urllib.parse

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def url_encode(value):
    return urllib.parse.quote(value, safe="")


def format_duration(seconds):
    if not seconds or seconds <= 0:
        return "--:--"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def sanitize_filename(name, max_length=180):
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "download"

    stem, ext = os.path.splitext(cleaned)
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"

    max_stem_length = max_length - len(ext)
    if len(stem) > max_stem_length:
        stem = stem[:max_stem_length].rstrip(" .")
    return f"{stem}{ext}"


def get_artist_str(song):
    artist = song.get("artist", "未知")
    if isinstance(artist, list):
        return ", ".join(str(item) for item in artist)
    return str(artist)


def normalize_song(song):
    artist = get_artist_str(song)
    has_hires = song.get("has_hires", False)
    return {
        "name": str(song.get("name", "未知")) + (" [Hi-Res]" if has_hires else ""),
        "artist": artist,
        "album": str(song.get("album", "未知")),
        "duration": format_duration(song.get("duration", 0)),
        "source": str(song.get("source", "未知")),
        "id": str(song.get("id", "")),
        "url_id": str(song.get("url_id", "")),
        "pic_id": str(song.get("pic_id", "")),
        "lyric_id": str(song.get("lyric_id", "")),
    }


def parse_selection(selection, total, *, warn=None):
    """解析 1,3,5-7 这样的选择字符串为 0-based 索引列表。

    Parameters
    ----------
    selection:
        用户输入字符串。
    total:
        总条目数。
    warn:
        可选的可调用对象，接收提示信息字符串。用于在反向区间时给用户可见提示。
    """
    indices = set()
    for part in selection.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                start_num = int(start)
                end_num = int(end)
            except ValueError:
                continue
            if start_num > end_num:
                if warn is not None:
                    warn(f"  ⚠ 已反转区间 {start_num}-{end_num} 为 {end_num}-{start_num}")
                start_num, end_num = end_num, start_num
            for index in range(start_num, min(end_num, total) + 1):
                if 1 <= index <= total:
                    indices.add(index - 1)
            continue

        try:
            index = int(part)
        except ValueError:
            continue
        if 1 <= index <= total:
            indices.add(index - 1)
    return sorted(indices)
