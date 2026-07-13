"""音频下载：重试、临时文件、原子重命名与元数据附加。"""

import contextlib
import os
import random
import shutil
import time
from collections.abc import Iterable
from typing import Any

from music_downloader.core.config import (
    COVER_TIMEOUT_MS,
    DOWNLOAD_RETRIES,
    DOWNLOAD_RETRY_BACKOFF_SEC,
    MIN_DOWNLOAD_BYTES,
    PROXY_BASE_URL,
    REQUEST_TIMEOUT_MS,
)
from music_downloader.core.console import console
from music_downloader.domain.formatting import get_artist_str
from music_downloader.infrastructure.files import safe_filename
from music_downloader.infrastructure.gdstudio import get_lyric, get_pic_url, get_play_url
from music_downloader.infrastructure.tags import embed_metadata

PathLike = str | os.PathLike[str]


def _retry_backoff() -> float:
    """下载重试的随机退避：基础值上下浮动 ±20%，避免 Cloudflare 风控。"""
    return random.uniform(
        DOWNLOAD_RETRY_BACKOFF_SEC * 0.8,
        DOWNLOAD_RETRY_BACKOFF_SEC * 1.2,
    )


def get_output_extension(bitrate: str) -> str:
    """根据音质返回文件扩展名，flac 返回 .flac，其余返回 .mp3。"""
    return ".flac" if bitrate == "flac" else ".mp3"


def build_output_path(save_dir: str, song: dict, bitrate: str) -> str:
    """根据歌曲信息和音质构建输出文件路径。

    文件名格式: [id] artist - name.ext
    """
    artist = get_artist_str(song)
    name = str(song.get("name", "未知"))
    song_id = str(song.get("id", ""))
    extension = get_output_extension(bitrate)
    filename = safe_filename(f"[{song_id}] {artist} - {name}{extension}")
    return os.path.join(save_dir, filename)


def cleanup_paths(paths: Iterable[PathLike] | None) -> None:
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


def _safe_embed_metadata(**kwargs: Any) -> bool:
    """在 downloader 内安全调用 embed_metadata。

    元数据写入失败会留下"无标签文件"且下次运行被"已存在"逻辑跳过。
    失败时返回 False，但已下载音频保留，只记录 warning。
    """
    try:
        embed_metadata(**kwargs)
        return True
    except Exception as exc:  # noqa: BLE001 - 兜底避免残缺文件
        console.print(f"  ⚠ 写入元数据失败: {exc}", style="yellow")
        return False


def _audio_response_error(content_type: str, body: bytes) -> str | None:
    """Return a reason for obvious upstream error documents, otherwise None."""
    mime = content_type.partition(";")[0].strip().lower()
    if mime == "text/html" or mime == "application/json" or mime.endswith("+json"):
        return f"响应类型为 {mime}"
    if mime in {"application/xml", "text/xml"} or mime.endswith("+xml"):
        return f"响应类型为 {mime}"

    prefix = body[:512]
    if prefix.startswith(b"\xef\xbb\xbf"):
        prefix = prefix[3:]
    prefix = prefix.lstrip(b"\x00\t\r\n ").lower()
    if prefix.startswith((b"<!doctype html", b"<html")):
        return "响应内容为 HTML"
    if prefix.startswith((b"{", b"[")):
        return "响应内容为 JSON"
    if prefix.startswith(b"<?xml"):
        return "响应内容为 XML"
    return None


def _download_body_to_file(
    context: Any,
    proxy_url: str,
    tmp_path: PathLike,
    filepath: PathLike,
) -> bool:
    """下载音频到临时文件并原子重命名。成功返回 True；任何失败返回 False 并清理 tmp。"""
    try:
        resp = context.request.get(proxy_url, timeout=REQUEST_TIMEOUT_MS)
    except Exception as exc:  # noqa: BLE001 - 网络层异常吞掉即可
        console.print(f"  ✗ 下载异常: {exc}", style="red")
        cleanup_paths([tmp_path])
        return False

    if not resp.ok:
        console.print(f"  ✗ 下载失败: HTTP {resp.status}", style="red")
        cleanup_paths([tmp_path])
        return False

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
            f"  ✗ 下载文件异常 (仅 {len(body)} 字节)，可能是错误响应",
            style="red",
        )
        cleanup_paths([tmp_path])
        return False

    response_error = _audio_response_error(resp.headers.get("content-type", ""), body)
    if response_error is not None:
        console.print(f"  ✗ 下载文件异常 ({response_error})，可能是错误响应", style="red")
        cleanup_paths([tmp_path])
        return False

    with open(tmp_path, "wb") as file_obj:
        file_obj.write(body)
    try:
        os.replace(tmp_path, filepath)
    except OSError as exc:
        console.print(f"  ✗ 移动临时文件失败: {exc}", style="red")
        console.print(
            "    目标目录可能与源不在同一盘符，请检查 -o 输出目录",
            style="yellow",
        )
        cleanup_paths([tmp_path])
        return False

    size_mb = len(body) / 1024 / 1024
    filename = os.path.basename(filepath)
    console.print(f"  ✓ 已保存: {filename} ({size_mb:.1f} MB)", style="green")
    return True


def _attach_metadata(
    filepath: PathLike,
    song: dict,
    index: int,
    total: int,
    download_lyric: bool,
    download_cover: bool,
    page: Any,
    context: Any,
    source: str,
    bitrate: str,
) -> bool:
    """拉歌词/封面并写入元数据。元数据失败只警告，不影响下载成功状态。"""
    cover_data = b""
    cover_mime = "image/jpeg"
    lyric_text = ""
    if download_lyric:
        lyric_text = get_lyric(page, song, source)
    if download_cover:
        pic_url = get_pic_url(page, song, source)
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
        console.print("  ⚠ 音频已下载，元数据写入失败已忽略", style="yellow")
    return True


def download_song(
    page: Any,
    context: Any,
    song: dict,
    source: str,
    save_dir: str,
    index: int = 0,
    total: int = 0,
    download_lyric: bool = True,
    download_cover: bool = True,
    bitrate: str = "320",
) -> str:
    name = str(song.get("name", "未知"))
    filepath = build_output_path(save_dir, song, bitrate)
    filename = os.path.basename(filepath)
    tmp_path = filepath + ".tmp"

    if os.path.exists(filepath):
        console.print(f"  ⊘ 已存在，跳过: {filename}", style="dim")
        return "skip"

    console.print(f"  获取播放链接: {name}...", style="cyan")
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        if attempt > 1:
            console.print(f"  重新获取播放链接: {name}...", style="cyan")

        play_url = get_play_url(page, song, source, bitrate)
        if not play_url:
            console.print("  ✗ 未获取到播放链接", style="red")
            if attempt >= DOWNLOAD_RETRIES:
                return "fail"
            console.print("  等待后重试...", style="dim")
            time.sleep(_retry_backoff())
            continue

        console.print(f"  下载中: {filename}...", style="cyan")
        proxy_url = f"{PROXY_BASE_URL}/{play_url}"
        if _download_body_to_file(context, proxy_url, tmp_path, filepath):
            ok = _attach_metadata(
                filepath=filepath,
                song=song,
                index=index,
                total=total,
                download_lyric=download_lyric,
                download_cover=download_cover,
                page=page,
                context=context,
                source=source,
                bitrate=bitrate,
            )
            return "success" if ok else "fail"

        if attempt >= DOWNLOAD_RETRIES:
            return "fail"
        console.print("  等待后重试...", style="dim")
        time.sleep(_retry_backoff())

    return "fail"
