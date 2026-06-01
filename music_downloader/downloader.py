import os
import time

from .api import get_lyric, get_pic_url, get_play_url
from .config import (
    COVER_TIMEOUT_MS,
    DOWNLOAD_RETRIES,
    MIN_DOWNLOAD_BYTES,
    PROXY_BASE_URL,
    REQUEST_TIMEOUT_MS,
)
from .metadata import embed_metadata
from .utils import get_artist_str, sanitize_filename


def get_output_extension(bitrate):
    return ".flac" if bitrate == "flac" else ".mp3"


def build_output_path(save_dir, song, bitrate):
    artist = get_artist_str(song)
    name = str(song.get("name", "未知"))
    song_id = str(song.get("id", ""))
    extension = get_output_extension(bitrate)
    filename = sanitize_filename(f"[{song_id}] {artist} - {name}{extension}")
    return os.path.join(save_dir, filename)


def cleanup_paths(paths):
    for path in paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


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
        print(f"  ⊘ 已存在，跳过: {filename}")
        return "skip"

    print(f"  获取播放链接: {name}...")
    play_url = get_play_url(page, song, source, version, bitrate)
    if not play_url:
        print("  ✗ 未获取到播放链接，跳过")
        return "fail"

    print(f"  下载中: {filename}...")
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        if attempt > 1:
            print(f"  重新获取播放链接: {name}...")
            play_url = get_play_url(page, song, source, version, bitrate)
            if not play_url:
                print("  ✗ 未获取到播放链接")
                if attempt < DOWNLOAD_RETRIES:
                    time.sleep(3)
                continue

        proxy_url = f"{PROXY_BASE_URL}/{play_url}"
        try:
            resp = context.request.get(proxy_url, timeout=REQUEST_TIMEOUT_MS)
            if not resp.ok:
                print(f"  ✗ 第 {attempt} 次下载失败: HTTP {resp.status}")
                if attempt < DOWNLOAD_RETRIES:
                    time.sleep(3)
                    continue
                return "fail"

            content_length = resp.headers.get("content-length")
            if content_length:
                try:
                    size_hint = int(content_length) / 1024 / 1024
                    print(f"  文件大小: 约 {size_hint:.1f} MB")
                except ValueError:
                    pass

            body = resp.body()
            if len(body) < MIN_DOWNLOAD_BYTES:
                print(
                    f"  ✗ 第 {attempt} 次下载文件异常 (仅 {len(body)} 字节)，可能是错误响应"
                )
                cleanup_paths([tmp_path])
                if attempt < DOWNLOAD_RETRIES:
                    time.sleep(3)
                    continue
                return "fail"

            with open(tmp_path, "wb") as file_obj:
                file_obj.write(body)
            os.replace(tmp_path, filepath)

            size_mb = len(body) / 1024 / 1024
            print(f"  ✓ 已保存: {filename} ({size_mb:.1f} MB)")

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
                    except Exception:
                        pass

            embed_metadata(
                filepath,
                song,
                index=index,
                total=total,
                cover_data=cover_data,
                cover_mime=cover_mime,
                lyric_text=lyric_text,
                bitrate=bitrate,
            )
            return "success"
        except Exception as exc:
            print(f"  ✗ 第 {attempt} 次下载失败: {exc}")
            cleanup_paths([filepath, tmp_path])
            if attempt < DOWNLOAD_RETRIES:
                print("  等待 3 秒后重试...")
                time.sleep(3)
            else:
                return "fail"

    return "fail"
