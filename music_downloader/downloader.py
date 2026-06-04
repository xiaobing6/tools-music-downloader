import contextlib
import os
import shutil
import time
from collections.abc import Iterable
from typing import Optional, Union

from .api import get_lyric, get_pic_url, get_play_url
from .config import (
    COVER_TIMEOUT_MS,
    DOWNLOAD_RETRIES,
    MIN_DOWNLOAD_BYTES,
    PROXY_BASE_URL,
    REQUEST_TIMEOUT_MS,
)
from .console import console
from .metadata import embed_metadata
from .utils import get_artist_str, sanitize_filename

PathLike = Union[str, "os.PathLike[str]"]


def get_output_extension(bitrate: str) -> str:
    return ".flac" if bitrate == "flac" else ".mp3"


def build_output_path(save_dir: str, song: dict, bitrate: str) -> str:
    artist = get_artist_str(song)
    name = str(song.get("name", "未知"))
    song_id = str(song.get("id", ""))
    extension = get_output_extension(bitrate)
    filename = sanitize_filename(f"[{song_id}] {artist} - {name}{extension}")
    return os.path.join(save_dir, filename)


def cleanup_paths(paths: Optional[Iterable[PathLike]]) -> None:
    """尽力删除给定文件/目录路径。缺失或失败时静默。"""
    if not paths:
        return
    for path in paths:
        if not path:
            continue
        if os.path.isdir(path):
            with contextlib.suppress(OSError):
                shutil.rmtree(path, ignore_errors=True)
            continue
        if os.path.exists(path):
            with contextlib.suppress(OSError):
                os.remove(path)


def _safe_embed_metadata(**kwargs) -> bool:
    """在 downloader 内安全调用 embed_metadata。

    元数据写入失败会留下"无标签文件"且下次运行被"已存在"逻辑跳过。
    失败时返回 False，由调用方决定是否删除产物。
    """
    try:
        embed_metadata(**kwargs)
        return True
    except Exception as exc:  # noqa: BLE001 - 兜底避免残缺文件
        console.print(f"  ⚠ 写入元数据失败: {exc}", style="yellow")
        return False


def download_song(
    page,
    context,
    song,
    source,
    version,
    save_dir,
    index=0,
    total=0,
    download_lyric=True,
    download_cover=True,
    bitrate="320",
):
    name = str(song.get("name", "未知"))
    filepath = build_output_path(save_dir, song, bitrate)
    filename = os.path.basename(filepath)
    tmp_path = filepath + ".tmp"

    if os.path.exists(filepath):
        console.print(f"  ⊘ 已存在，跳过: {filename}", style="dim")
        return "skip"

    console.print(f"  获取播放链接: {name}...", style="cyan")
    play_url = get_play_url(page, song, source, version, bitrate)
    if not play_url:
        console.print("  ✗ 未获取到播放链接，跳过", style="red")
        return "fail"

    console.print(f"  下载中: {filename}...", style="cyan")
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        if attempt > 1:
            console.print(f"  重新获取播放链接: {name}...", style="cyan")
            play_url = get_play_url(page, song, source, version, bitrate)
            if not play_url:
                console.print("  ✗ 未获取到播放链接", style="red")
                if attempt < DOWNLOAD_RETRIES:
                    time.sleep(3)
                continue

        proxy_url = f"{PROXY_BASE_URL}/{play_url}"
        try:
            resp = context.request.get(proxy_url, timeout=REQUEST_TIMEOUT_MS)
            if not resp.ok:
                console.print(
                    f"  ✗ 第 {attempt} 次下载失败: HTTP {resp.status}",
                    style="red",
                )
                if attempt < DOWNLOAD_RETRIES:
                    time.sleep(3)
                    continue
                return "fail"

            content_length = resp.headers.get("content-length")
            if content_length:
                try:
                    size_hint = int(content_length) / 1024 / 1024
                    console.print(f"  文件大小: 约 {size_hint:.1f} MB", style="dim")
                except ValueError:
                    pass

            body = resp.body()
            if len(body) < MIN_DOWNLOAD_BYTES:
                console.print(
                    f"  ✗ 第 {attempt} 次下载文件异常 (仅 {len(body)} 字节)，可能是错误响应",
                    style="red",
                )
                cleanup_paths([tmp_path])
                if attempt < DOWNLOAD_RETRIES:
                    time.sleep(3)
                    continue
                return "fail"

            with open(tmp_path, "wb") as file_obj:
                file_obj.write(body)
            try:
                os.replace(tmp_path, filepath)
            except OSError as exc:
                console.print(
                    f"  ✗ 移动临时文件失败: {exc}",
                    style="red",
                )
                console.print(
                    "    目标目录可能与源不在同一盘符，请检查 -o 输出目录",
                    style="yellow",
                )
                cleanup_paths([tmp_path])
                if attempt < DOWNLOAD_RETRIES:
                    time.sleep(3)
                    continue
                return "fail"

            size_mb = len(body) / 1024 / 1024
            console.print(f"  ✓ 已保存: {filename} ({size_mb:.1f} MB)", style="green")

            cover_data = b""
            cover_mime = "image/jpeg"
            lyric_text = ""
            if download_lyric:
                lyric_text = get_lyric(page, song, source, version)
            if download_cover:
                pic_url = get_pic_url(page, song, source, version)
                if pic_url:
                    try:
                        cover_resp = context.request.get(pic_url, timeout=COVER_TIMEOUT_MS)
                        if cover_resp.ok:
                            cover_data = cover_resp.body()
                            cover_mime = cover_resp.headers.get("content-type", "image/jpeg")
                        else:
                            console.print(
                                f"  ⚠ 封面下载失败: HTTP {cover_resp.status}",
                                style="yellow",
                            )
                    except Exception as exc:  # noqa: BLE001
                        console.print(f"  ⚠ 封面下载异常: {exc}", style="yellow")

            embedded = _safe_embed_metadata(
                filepath=filepath,
                song=song,
                index=index,
                total=total,
                cover_data=cover_data,
                cover_mime=cover_mime,
                lyric_text=lyric_text,
                bitrate=bitrate,
            )
            if not embedded:
                # 删除残缺文件，避免下次被"已存在"逻辑永久跳过
                cleanup_paths([filepath, tmp_path])
                return "fail"
            return "success"
        except Exception as exc:
            console.print(f"  ✗ 第 {attempt} 次下载失败: {exc}", style="red")
            cleanup_paths([filepath, tmp_path])
            if attempt < DOWNLOAD_RETRIES:
                console.print("  等待 3 秒后重试...", style="dim")
                time.sleep(3)
            else:
                return "fail"

    return "fail"
