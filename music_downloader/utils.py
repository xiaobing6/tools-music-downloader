"""通用工具函数：URL 编码、文件名清理、歌曲字段格式化等。"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from typing import Any


def url_encode(value: str) -> str:
    """对字符串做 URL 编码，不保留安全字符。"""
    return urllib.parse.quote(value, safe="")


def format_duration(seconds: int | float | None) -> str:
    """将秒数格式化为 m:ss，无效值返回 --:--。"""
    if not seconds or seconds <= 0:
        return "--:--"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}:{secs:02d}"


def sanitize_filename(name: str, max_length: int = 180) -> str:
    """清理文件名中的非法字符并截断超长名称。

    Args:
        name: 原始文件名。
        max_length: 文件名最大长度（含扩展名）。

    Returns:
        清理后的安全文件名。
    """
    from music_downloader.infrastructure.files import safe_filename

    return safe_filename(name, max_length=max_length)


def get_artist_str(song: dict[str, Any]) -> str:
    """从歌曲字典中提取歌手名，列表类型用逗号拼接。"""
    artist = song.get("artist", "未知")
    if isinstance(artist, list):
        return ", ".join(str(item) for item in artist)
    return str(artist)


def normalize_song(song: dict[str, Any]) -> dict[str, str]:
    """把搜索接口返回的原始歌曲对象规整为展示用结构。

    字段含义:
      id       — 站点搜索/展示用的歌曲标识（用户可见的"歌曲 ID"）。
      url_id   — 取播放链接时真正使用的标识（部分源与 id 不同）。
      pic_id   — 封面图 API 用的标识。
      lyric_id — 歌词 API 用的标识。

    文件名取自 id（用户可读）；下载走 url_id（get_play_url 内部 url_id or id）。
    """
    from music_downloader.infrastructure.files import normalize_song_dict

    return normalize_song_dict(song)


def parse_selection(
    selection: str,
    total: int,
    *,
    warn: Callable[[str], None] | None = None,
) -> list[int]:
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
    indices: set[int] = set()
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
