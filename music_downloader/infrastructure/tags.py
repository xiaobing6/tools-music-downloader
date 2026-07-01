"""MP3/FLAC 音频文件元数据（ID3 / Vorbis Comment）写入。"""

from __future__ import annotations

from typing import Any

from music_downloader.console import console
from music_downloader.domain.formatting import get_artist_str


def embed_metadata(
    filepath: str,
    song: dict[str, Any],
    index: int = 0,
    total: int = 0,
    cover_data: bytes = b"",
    cover_mime: str = "image/jpeg",
    lyric_text: str = "",
    bitrate: str = "320",
) -> None:
    """根据文件类型写入元数据，FLAC 走 embed_flac_tags，其余走 embed_id3_tags。"""
    if bitrate == "flac" or filepath.lower().endswith(".flac"):
        return embed_flac_tags(
            filepath,
            song,
            index=index,
            total=total,
            cover_data=cover_data,
            cover_mime=cover_mime,
            lyric_text=lyric_text,
        )
    return embed_id3_tags(
        filepath,
        song,
        index=index,
        total=total,
        cover_data=cover_data,
        cover_mime=cover_mime,
        lyric_text=lyric_text,
    )


def embed_id3_tags(
    filepath: str,
    song: dict[str, Any],
    index: int = 0,
    total: int = 0,
    cover_data: bytes = b"",
    cover_mime: str = "image/jpeg",
    lyric_text: str = "",
) -> None:
    """向 MP3 文件写入 ID3v2 标签（标题、歌手、专辑、曲目号、封面、歌词）。"""
    try:
        from mutagen.id3 import APIC, TALB, TIT2, TPE1, TRCK, USLT
        from mutagen.mp3 import MP3
    except ImportError:
        console.print(
            "  ⚠ 未安装 mutagen，已跳过 MP3 元数据写入。请运行: pip install -r requirements.txt",
            style="yellow",
        )
        return

    try:
        audio = MP3(filepath)
        if audio.tags is None:
            audio.add_tags()
    except Exception:
        try:
            audio = MP3(filepath)
            audio.add_tags()
        except Exception as exc:
            console.print(f"  ⚠ 无法写入 ID3 标签: {exc}", style="yellow")
            return

    tags = audio.tags
    if tags is None:
        console.print("  ⚠ 无法写入 ID3 标签: 未能初始化标签", style="yellow")
        return

    name = str(song.get("name", ""))
    if name:
        tags.add(TIT2(encoding=3, text=name))

    artist = get_artist_str(song)
    if artist:
        tags.add(TPE1(encoding=3, text=artist))

    album = str(song.get("album", ""))
    if album:
        tags.add(TALB(encoding=3, text=album))

    if total > 0 and index > 0:
        tags.add(TRCK(encoding=3, text=f"{index}/{total}"))

    if cover_data:
        tags.add(APIC(encoding=3, mime=cover_mime, type=3, desc="Cover", data=cover_data))

    if lyric_text:
        tags.add(USLT(encoding=3, lang="zho", desc="Lyrics", text=lyric_text))

    try:
        audio.save()
        console.print(f"  ✓ ID3 标签已写入: {name}", style="green")
    except Exception as exc:
        console.print(f"  ⚠ 保存 ID3 标签失败: {exc}", style="yellow")


def embed_flac_tags(
    filepath: str,
    song: dict[str, Any],
    index: int = 0,
    total: int = 0,
    cover_data: bytes = b"",
    cover_mime: str = "image/jpeg",
    lyric_text: str = "",
) -> None:
    """向 FLAC 文件写入 Vorbis Comment 标签和封面图片。"""
    try:
        from mutagen.flac import FLAC, Picture
    except ImportError:
        console.print(
            "  ⚠ 未安装 mutagen，已跳过 FLAC 元数据写入。请运行: pip install -r requirements.txt",
            style="yellow",
        )
        return

    try:
        audio = FLAC(filepath)
    except Exception as exc:
        console.print(f"  ⚠ 无法写入 FLAC 标签: {exc}", style="yellow")
        return

    name = str(song.get("name", ""))
    artist = get_artist_str(song)
    album = str(song.get("album", ""))

    if name:
        audio["title"] = name
    if artist:
        audio["artist"] = artist
    if album:
        audio["album"] = album
    if total > 0 and index > 0:
        audio["tracknumber"] = str(index)
        audio["tracktotal"] = str(total)
    if lyric_text:
        audio["lyrics"] = lyric_text
    if cover_data:
        audio.clear_pictures()
        picture = Picture()
        picture.type = 3
        picture.mime = cover_mime or "image/jpeg"
        picture.desc = "Cover"
        picture.data = cover_data
        audio.add_picture(picture)

    try:
        audio.save()
        console.print(f"  ✓ FLAC 标签已写入: {name}", style="green")
    except Exception as exc:
        console.print(f"  ⚠ 保存 FLAC 标签失败: {exc}", style="yellow")
