import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.parse

from mutagen.id3 import ID3, TIT2, TPE1, TALB, TRCK, TCON, APIC, USLT, ID3NoHeaderError
from mutagen.mp3 import MP3
from playwright.sync_api import sync_playwright

BASE_URL = "https://music.gdstudio.org"
HOSTNAME = "music.gdstudio.org"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
DEFAULT_KEYWORD = "Beyond"
DEFAULT_SOURCE = "netease"
DEFAULT_NUMBER = 20
MAX_PER_PAGE = 99
VALID_SOURCES = [
    "netease", "migu", "kuwo", "ytmusic", "tidal",
    "qobuz", "deezer", "spotify", "tencent", "ximalaya",
    "joox", "apple",
]
VALID_FORMATS = ["table", "json", "list"]
VALID_BITRATES = ["128", "192", "320", "flac"]
SEARCH_TYPE_MAP = {
    "song": "search",
    "album": "search_album",
    "playlist": "search_playlist",
}


def url_encode(s: str) -> str:
    encoded = urllib.parse.quote(s, safe="")
    encoded = encoded.replace("(", "%28")
    encoded = encoded.replace(")", "%29")
    encoded = encoded.replace("*", "%2A")
    encoded = encoded.replace("'", "%27")
    encoded = encoded.replace("!", "%21")
    return encoded


def compute_signature(hostname: str, version: str, timestamp: str, search_id: str) -> str:
    padded_version = "".join(p.zfill(2) for p in version.split("."))
    ts_first9 = str(timestamp)[:9]
    signing_string = f"{hostname}|{padded_version}|{ts_first9}|{search_id}"
    return hashlib.md5(signing_string.encode()).hexdigest()[-8:].upper()


def format_duration(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "--:--"
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', name)


def get_artist_str(song: dict) -> str:
    artist = song.get("artist", "未知")
    if isinstance(artist, list):
        artist = ", ".join(artist)
    return artist


def normalize_song(song: dict) -> dict:
    artist = get_artist_str(song)
    has_hires = song.get("has_hires", False)
    return {
        "name": song.get("name", "未知") + (" [Hi-Res]" if has_hires else ""),
        "artist": artist,
        "album": song.get("album", "未知"),
        "duration": format_duration(song.get("duration", 0)),
        "source": song.get("source", "未知"),
        "id": str(song.get("id", "")),
        "url_id": str(song.get("url_id", "")),
        "pic_id": str(song.get("pic_id", "")),
        "lyric_id": str(song.get("lyric_id", "")),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="music.gdstudio.org 音乐搜索与下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python download.py -k "周杰伦"
  python download.py -k "Beyond" -n 5
  python download.py -k "Beyond" -t album
  python download.py -k "Beyond" -o "D:\\Music"
  python download.py -k "Beyond" --search-only
  python download.py -i""",
    )
    parser.add_argument("-k", "--keyword", default=DEFAULT_KEYWORD, help=f"搜索关键词 (默认: {DEFAULT_KEYWORD})")
    parser.add_argument("-s", "--source", default=DEFAULT_SOURCE, choices=VALID_SOURCES, help=f"音乐源 (默认: {DEFAULT_SOURCE})")
    parser.add_argument("-n", "--number", type=int, default=DEFAULT_NUMBER, help=f"获取结果总数 (默认: {DEFAULT_NUMBER}, 上限无限制，脚本自动分页)")
    parser.add_argument("-t", "--type", default="song", choices=SEARCH_TYPE_MAP.keys(), dest="search_type", help="搜索类型: song/album/playlist (默认: song)")
    parser.add_argument("-o", "--output", default="", dest="output_dir", help="下载目录 (默认: 脚本同级 downloads/)")
    parser.add_argument("-f", "--format", default="table", choices=VALID_FORMATS, dest="output_format", help="输出格式 (默认: table)")
    parser.add_argument("-b", "--bitrate", default="320", choices=VALID_BITRATES, help="音质选择: 128/192/320/flac (默认: 320)")
    parser.add_argument("--search-only", action="store_true", help="只搜索不下载")
    parser.add_argument("--select", action="store_true", help="搜索后选择要下载的歌曲")
    parser.add_argument("--no-lyric", action="store_true", help="不下载歌词（默认下载）")
    parser.add_argument("--no-cover", action="store_true", help="不嵌入封面（默认嵌入）")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式，浏览器保持运行可反复搜索")
    return parser.parse_args()


def wait_for_cloudflare(page, max_retries: int = 3) -> bool:
    for attempt in range(1, max_retries + 1):
        cf_cookie = None
        for cookie in page.context.cookies():
            if cookie["name"] == "cf_clearance":
                cf_cookie = cookie["value"]
                break
        if cf_cookie:
            print(f"  ✓ Cloudflare 验证通过 (第 {attempt} 次尝试)")
            return True
        if attempt < max_retries:
            print(f"  ⚠ 未检测到 cf_clearance，第 {attempt + 1} 次重试...")
            page.reload(wait_until="networkidle", timeout=60000)
    return False


def refresh_cloudflare(page) -> bool:
    print("  ⚠ Cloudflare 验证可能已过期，尝试重新验证...")
    page.reload(wait_until="networkidle", timeout=60000)
    return wait_for_cloudflare(page)


def fetch_api(page, body: str) -> tuple[int, str]:
    result = page.evaluate(
        """async (body) => {
            const resp = await fetch('/api.php', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json, text/javascript, */*; q=0.01'
                },
                body: body
            });
            return { status: resp.status, text: await resp.text() };
        }""",
        body,
    )
    return result["status"], result["text"]


def get_timestamp(page) -> str:
    return page.evaluate(
        """async () => {
            const resp = await fetch('/time');
            return await resp.text();
        }"""
    )


def search_with_pagination(page, keyword: str, source: str, search_type: str, total: int, version: str) -> list:
    all_results = []
    remaining = total
    current_page = 1
    total_pages = math.ceil(total / MAX_PER_PAGE)
    encoded_name = url_encode(keyword)
    api_type = SEARCH_TYPE_MAP.get(search_type, "search")
    cf_retry_count = 0

    while remaining > 0:
        count = min(remaining, MAX_PER_PAGE)
        page_label = f"第 {current_page}/{total_pages} 页" if total_pages > 1 else ""
        if page_label:
            print(f"      {page_label}: 请求 {count} 条...")

        timestamp = get_timestamp(page)
        signature = compute_signature(HOSTNAME, version, timestamp, encoded_name)

        body = f"types={api_type}&count={count}&source={source}&pages={current_page}&name={encoded_name}&s={signature}"
        status, result_text = fetch_api(page, body)

        if status != 200:
            if status == 401:
                print(f"  ✗ 请求被拒绝 (HTTP {status}) — 签名验证失败，站点可能已更新版本")
            elif status == 403:
                print(f"  ✗ 请求被拒绝 (HTTP {status}) — Cloudflare 验证可能已过期")
                cf_retry_count += 1
                if cf_retry_count <= 2 and refresh_cloudflare(page):
                    continue
            elif status == 502:
                print(f"  ✗ 服务器连接中断 (HTTP {status}) — 请稍后重试")
            else:
                print(f"  ✗ 请求失败 (HTTP {status})")
            print(f"  响应内容: {result_text[:200]}")
            break

        try:
            data = json.loads(result_text)
        except json.JSONDecodeError:
            print(f"  ✗ 响应解析失败，原始内容: {result_text[:500]}")
            break

        if not isinstance(data, list) or len(data) == 0:
            break

        all_results.extend(data)
        remaining -= len(data)
        current_page += 1

        if len(data) < count:
            break

    return all_results[:total]


def get_play_url(page, song: dict, source: str, version: str, bitrate: str = "320") -> str:
    url_id = str(song.get("url_id", song.get("id", "")))
    if not url_id:
        return ""
    for attempt in range(1, 3):
        timestamp = get_timestamp(page)
        encoded_id = url_encode(url_id)
        signature = compute_signature(HOSTNAME, version, timestamp, encoded_id)
        body = f"types=url&id={encoded_id}&source={source}&br={bitrate}&s={signature}"
        status, result_text = fetch_api(page, body)

        if status == 403:
            print(f"  ✗ 获取播放链接失败 (HTTP 403) — Cloudflare 验证可能已过期")
            if refresh_cloudflare(page):
                continue
            return ""

        if status != 200:
            print(f"  ✗ 获取播放链接失败 (HTTP {status})")
            return ""

        try:
            data = json.loads(result_text)
            return data.get("url", "")
        except json.JSONDecodeError:
            print(f"  ✗ 解析播放链接响应失败")
            return ""

    return ""


def get_lyric(page, song: dict, source: str, version: str) -> str:
    lyric_id = str(song.get("lyric_id", ""))
    if not lyric_id:
        return ""
    for attempt in range(1, 3):
        timestamp = get_timestamp(page)
        encoded_id = url_encode(lyric_id)
        signature = compute_signature(HOSTNAME, version, timestamp, encoded_id)
        body = f"types=lyric&id={encoded_id}&source={source}&s={signature}"
        status, result_text = fetch_api(page, body)

        if status == 403:
            if refresh_cloudflare(page):
                continue
            return ""

        if status != 200:
            return ""

        try:
            data = json.loads(result_text)
            return data.get("lyric", "")
        except json.JSONDecodeError:
            return ""

    return ""


def get_pic_url(page, song: dict, source: str, version: str) -> str:
    pic_id = str(song.get("pic_id", ""))
    if not pic_id:
        return ""
    for attempt in range(1, 3):
        timestamp = get_timestamp(page)
        encoded_id = url_encode(pic_id)
        signature = compute_signature(HOSTNAME, version, timestamp, encoded_id)
        body = f"types=pic&id={encoded_id}&source={source}&s={signature}"
        status, result_text = fetch_api(page, body)

        if status == 403:
            if refresh_cloudflare(page):
                continue
            return ""

        if status != 200:
            return ""

        try:
            data = json.loads(result_text)
            return data.get("url", "")
        except json.JSONDecodeError:
            return ""

    return ""


def embed_id3_tags(filepath: str, song: dict, index: int = 0, total: int = 0, cover_data: bytes = b"", cover_mime: str = "image/jpeg", lyric_text: str = ""):
    """将歌曲元数据写入 MP3 文件的 ID3v2 标签"""
    try:
        audio = MP3(filepath)
        # 如果文件没有 ID3 标签，初始化一个
        if audio.tags is None:
            audio.add_tags()
    except Exception:
        try:
            audio = MP3(filepath)
            audio.add_tags()
        except Exception as e:
            print(f"  ⚠ 无法写入 ID3 标签: {e}")
            return

    tags = audio.tags

    # 标题
    name = song.get("name", "")
    if name:
        tags.add(TIT2(encoding=3, text=name))

    # 艺术家
    artist = get_artist_str(song)
    if artist:
        tags.add(TPE1(encoding=3, text=artist))

    # 专辑
    album = song.get("album", "")
    if album:
        tags.add(TALB(encoding=3, text=album))

    # 曲目编号
    if total > 0 and index > 0:
        tags.add(TRCK(encoding=3, text=f"{index}/{total}"))

    if cover_data:
        tags.add(APIC(encoding=3, mime=cover_mime, type=3, desc="Cover", data=cover_data))

    if lyric_text:
        tags.add(USLT(encoding=3, lang="zho", desc="Lyrics", text=lyric_text))

    try:
        audio.save()
        print(f"  ✓ ID3 标签已写入: {name}")
    except Exception as e:
        print(f"  ⚠ 保存 ID3 标签失败: {e}")


def download_song(page, context, song: dict, source: str, version: str, save_dir: str, index: int = 0, total: int = 0, download_lyric: bool = True, download_cover: bool = True, bitrate: str = "320") -> str:
    artist = get_artist_str(song)
    name = song.get("name", "未知")
    song_id = str(song.get("id", ""))
    filename = sanitize_filename(f"[{song_id}] {artist} - {name}.mp3")
    filepath = os.path.join(save_dir, filename)

    if os.path.exists(filepath):
        print(f"  ⊘ 已存在，跳过: {filename}")
        return "skip"

    print(f"  获取播放链接: {name}...")
    play_url = get_play_url(page, song, source, version, bitrate)
    if not play_url:
        print(f"  ✗ 未获取到播放链接，跳过")
        return "fail"

    print(f"  下载中: {filename}...")
    max_retries = 2
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            print(f"  重新获取播放链接: {name}...")
            play_url = get_play_url(page, song, source, version, bitrate)
            if not play_url:
                print(f"  ✗ 未获取到播放链接，跳过")
                if attempt < max_retries:
                    time.sleep(3)
                continue
        proxy_url = f"https://music-proxy.gdstudio.org/{play_url}"
        try:
            resp = context.request.get(proxy_url, timeout=300000)
            if not resp.ok:
                print(f"  ✗ 下载失败: HTTP {resp.status}")
                return "fail"

            content_length = resp.headers.get("content-length")
            if content_length:
                size_hint = int(content_length) / 1024 / 1024
                print(f"  文件大小: 约 {size_hint:.1f} MB")

            body = resp.body()
            if len(body) < 10240:
                print(f"  ✗ 下载文件异常 (仅 {len(body)} 字节)，可能是错误响应")
                if attempt < max_retries:
                    time.sleep(3)
                continue

            tmp_path = filepath + ".tmp"
            with open(tmp_path, "wb") as f:
                f.write(body)
            os.rename(tmp_path, filepath)

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
                        cover_resp = context.request.get(pic_url, timeout=30000)
                        if cover_resp.ok:
                            cover_data = cover_resp.body()
                            cover_mime = cover_resp.headers.get("content-type", "image/jpeg")
                    except Exception:
                        pass

            embed_id3_tags(filepath, song, index, total, cover_data=cover_data, cover_mime=cover_mime, lyric_text=lyric_text)

            return "success"
        except Exception as e:
            print(f"  ✗ 第 {attempt} 次下载失败: {e}")
            for p in (filepath, filepath + ".tmp"):
                if os.path.exists(p):
                    os.remove(p)
            if attempt < max_retries:
                print(f"  等待 3 秒后重试...")
                time.sleep(3)
            else:
                return "fail"

    return "fail"


def display_table(data: list, keyword: str):
    songs = [normalize_song(s) for s in data]
    headers = ["#", "歌名", "歌手", "专辑", "时长", "来源", "ID"]
    rows = []
    for i, s in enumerate(songs, 1):
        rows.append([str(i), s["name"], s["artist"], s["album"], s["duration"], s["source"], s["id"]])

    col_widths = [len(h) for h in headers]
    for row in rows:
        for j, cell in enumerate(row):
            cell_len = 0
            for ch in cell:
                cell_len += 2 if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f' or '\uff00' <= ch <= '\uffef' else 1
            col_widths[j] = max(col_widths[j], cell_len)

    def pad_cell(text: str, width: int) -> str:
        display_len = 0
        for ch in text:
            display_len += 2 if '\u4e00' <= ch <= '\u9fff' or '\u3000' <= ch <= '\u303f' or '\uff00' <= ch <= '\uffef' else 1
        return text + " " * (width - display_len)

    sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_line = "|" + "|".join(" " + pad_cell(h, col_widths[i]) + " " for i, h in enumerate(headers)) + "|"

    print(sep)
    print(header_line)
    print(sep)
    for row in rows:
        line = "|" + "|".join(" " + pad_cell(cell, col_widths[i]) + " " for i, cell in enumerate(row)) + "|"
        print(line)
    print(sep)
    print(f"共 {len(data)} 首歌曲 (关键词: \"{keyword}\")")


def display_list(data: list, keyword: str):
    print("=" * 70)
    for i, song in enumerate(data, 1):
        s = normalize_song(song)
        print(f"  {i:2d}. {s['name']}")
        print(f"      歌手: {s['artist']} | 专辑: {s['album']} | 时长: {s['duration']} | 来源: {s['source']} | ID: {s['id']}")
        print()
    print(f"共找到 {len(data)} 首歌曲 (关键词: \"{keyword}\")")
    print("=" * 70)


def display_results(data, keyword: str, output_format: str = "table"):
    if output_format == "json":
        print(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_format == "list":
        display_list(data, keyword)
    else:
        display_table(data, keyword)


def parse_selection(selection: str, total: int) -> list:
    indices = set()
    for part in selection.split(","):
        part = part.strip()
        if "-" in part:
            try:
                start, end = part.split("-", 1)
                for i in range(int(start), min(int(end) + 1, total + 1)):
                    if 1 <= i <= total:
                        indices.add(i - 1)
            except ValueError:
                continue
        else:
            try:
                i = int(part)
                if 1 <= i <= total:
                    indices.add(i - 1)
            except ValueError:
                continue
    return sorted(indices)


def do_search_and_download(page, context, keyword, source, search_type, number, version, save_dir, output_format, search_only, select=False, download_lyric=True, download_cover=True, bitrate="320"):
    print(f"搜索 \"{keyword}\" (来源: {source}, 类型: {search_type}, 数量: {number})...")
    results = search_with_pagination(page, keyword, source, search_type, number, version)

    if not results:
        print("  未找到结果")
        return

    display_results(results, keyword, output_format=output_format)

    if search_only:
        return

    if select:
        try:
            selection = input(f"\n请选择要下载的歌曲 (如: 1,3,5-7，共 {len(results)} 首): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not selection:
            print("  未选择，跳过下载")
            return
        indices = parse_selection(selection, len(results))
        if not indices:
            print("  无有效选择，跳过下载")
            return
        results = [results[i] for i in indices]
        print(f"  已选择 {len(results)} 首歌曲")

    if len(results) < number:
        print(f"\n实际找到 {len(results)} 条 (请求 {number} 条)，下载已有的结果")

    print(f"\n开始下载 ({len(results)} 首)...")
    success = 0
    fail = 0
    skip = 0

    for i, song in enumerate(results):
        result = download_song(page, context, song, source, version, save_dir, i + 1, len(results), download_lyric=download_lyric, download_cover=download_cover, bitrate=bitrate)
        if result == "success":
            success += 1
        elif result == "skip":
            skip += 1
        else:
            fail += 1
        if i < len(results) - 1:
            time.sleep(1)

    print(f"\n下载完成: 成功 {success} 首 / 失败 {fail} 首 / 跳过 {skip} 首")


def interactive_mode(page, context, version, args):
    source = args.source
    search_type = args.search_type
    number = args.number
    save_dir = args.output_dir if args.output_dir else os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")
    os.makedirs(save_dir, exist_ok=True)
    output_format = args.output_format

    print("\n=== 交互模式 ===")
    print("输入关键词搜索并下载，输入 q 退出")
    print("命令: s <来源>  切换音乐源 | n <数量>  修改数量 | so  只搜索不下载")
    print(f"当前设置: 来源={source}, 类型={search_type}, 数量={number}")
    print()

    while True:
        try:
            user_input = input("搜索: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n退出")
            break

        if not user_input:
            continue
        if user_input.lower() == "q":
            print("退出")
            break

        if user_input.lower().startswith("s ") and len(user_input) > 2:
            new_source = user_input[2:].strip()
            if new_source in VALID_SOURCES:
                source = new_source
                print(f"  ✓ 音乐源已切换为: {source}")
            else:
                print(f"  ✗ 无效来源: {new_source}，可选: {', '.join(VALID_SOURCES)}")
            continue

        if user_input.lower().startswith("n ") and len(user_input) > 2:
            try:
                number = int(user_input[2:].strip())
                if number < 1:
                    raise ValueError
                print(f"  ✓ 数量已修改为: {number}")
            except ValueError:
                print(f"  ✗ 无效数量，请输入正整数")
            continue

        if user_input.lower() == "so":
            search_only = True
        else:
            search_only = False

        keyword = user_input if not search_only else ""
        if not keyword:
            try:
                keyword = input("关键词: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            if not keyword:
                continue

        do_search_and_download(page, context, keyword, source, search_type, number, version, save_dir, output_format, search_only=search_only, select=False, download_lyric=not args.no_lyric, download_cover=not args.no_cover, bitrate=args.bitrate)
        print()


def main():
    args = parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    save_dir = args.output_dir if args.output_dir else os.path.join(script_dir, "downloads")
    os.makedirs(save_dir, exist_ok=True)

    with sync_playwright() as p:
        print("正在访问页面，等待 Cloudflare 验证...")
        browser = p.chromium.launch(channel="chrome", headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        try:
            page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
        except Exception as e:
            print(f"  ✗ 页面加载失败: {e}")
            browser.close()
            sys.exit(1)

        cf_passed = wait_for_cloudflare(page)

        if not cf_passed:
            print("  ⚠ 无头模式未通过 Cloudflare 验证，尝试有头模式...")
            browser.close()
            browser = p.chromium.launch(channel="chrome", headless=False)
            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()
            page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            cf_passed = wait_for_cloudflare(page)

        if not cf_passed:
            print("  ✗ Cloudflare 验证未通过")
            browser.close()
            sys.exit(1)

        version = page.evaluate("typeof mkPlayer !== 'undefined' ? mkPlayer.version : ''")
        if not version:
            print("  ⚠ 未能从页面获取 mkPlayer.version，使用默认值")
            version = "2026.5.10"
        print(f"  ✓ 版本: {version}")

        if args.interactive:
            interactive_mode(page, context, version, args)
        else:
            do_search_and_download(
                page, context, args.keyword, args.source, args.search_type,
                args.number, version, save_dir, args.output_format, args.search_only,
                select=args.select, download_lyric=not args.no_lyric, download_cover=not args.no_cover, bitrate=args.bitrate
            )

        browser.close()


if __name__ == "__main__":
    main()
