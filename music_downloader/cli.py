import argparse
import os
import sys
import time

from .api import search_with_pagination, wait_for_cloudflare
from .config import (
    BASE_URL,
    DEFAULT_BITRATE,
    DEFAULT_KEYWORD,
    DEFAULT_NUMBER,
    DEFAULT_SOURCE,
    FALLBACK_VERSION,
    SEARCH_TYPE_MAP,
    USER_AGENT,
    VALID_BITRATES,
    VALID_FORMATS,
    VALID_SOURCES,
)
from .display import display_results
from .downloader import download_song
from .models import RunOptions
from .utils import parse_selection


def positive_int(value):
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是正整数") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("必须是正整数")
    return parsed


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="music.gdstudio.org 音乐搜索与下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python music_download.py -k "周杰伦"
  python music_download.py -k "Beyond" -n 5
  python music_download.py -k "Beyond" -t album
  python music_download.py -k "Beyond" -o "D:\\Music"
  python music_download.py -k "Beyond" --search-only
  python music_download.py -i""",
    )
    parser.add_argument("-k", "--keyword", default=DEFAULT_KEYWORD, help=f"搜索关键词 (默认: {DEFAULT_KEYWORD})")
    parser.add_argument("-s", "--source", default=DEFAULT_SOURCE, choices=VALID_SOURCES, help=f"音乐源 (默认: {DEFAULT_SOURCE})")
    parser.add_argument("-n", "--number", type=positive_int, default=DEFAULT_NUMBER, help=f"获取结果总数 (默认: {DEFAULT_NUMBER}, 自动分页)")
    parser.add_argument("-t", "--type", default="song", choices=SEARCH_TYPE_MAP.keys(), dest="search_type", help="搜索类型: song/album/playlist (默认: song)")
    parser.add_argument("-o", "--output", default="", dest="output_dir", help="下载目录 (默认: 脚本同级 downloads/)")
    parser.add_argument("-f", "--format", default="table", choices=VALID_FORMATS, dest="output_format", help="输出格式 (默认: table)")
    parser.add_argument("-b", "--bitrate", default=DEFAULT_BITRATE, choices=VALID_BITRATES, help=f"音质选择: 128/192/320/flac (默认: {DEFAULT_BITRATE})")
    parser.add_argument("--search-only", action="store_true", help="只搜索不下载")
    parser.add_argument("--select", action="store_true", help="搜索后选择要下载的歌曲")
    parser.add_argument("--no-lyric", action="store_true", help="不下载歌词（默认下载）")
    parser.add_argument("--no-cover", action="store_true", help="不嵌入封面（默认嵌入）")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互模式，浏览器保持运行可反复搜索")
    return parser.parse_args(argv)


def make_run_options(args, script_dir):
    save_dir = args.output_dir if args.output_dir else os.path.join(script_dir, "downloads")
    return RunOptions(
        keyword=args.keyword,
        source=args.source,
        search_type=args.search_type,
        number=args.number,
        output_dir=save_dir,
        output_format=args.output_format,
        search_only=args.search_only,
        select=args.select,
        download_lyric=not args.no_lyric,
        download_cover=not args.no_cover,
        bitrate=args.bitrate,
    )


def do_search_and_download(page, context, options):
    print(
        f'搜索 "{options.keyword}" (来源: {options.source}, 类型: {options.search_type}, 数量: {options.number})...'
    )
    results = search_with_pagination(
        page,
        options.keyword,
        options.source,
        options.search_type,
        options.number,
        options.version,
    )

    if not results:
        print("  未找到结果")
        return

    display_results(results, options.keyword, output_format=options.output_format)

    if options.search_only:
        return

    if options.select:
        try:
            selection = input(
                f"\n请选择要下载的歌曲 (如: 1,3,5-7，共 {len(results)} 首): "
            ).strip()
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
        results = [results[index] for index in indices]
        print(f"  已选择 {len(results)} 首歌曲")

    if len(results) < options.number:
        print(f"\n实际找到 {len(results)} 条 (请求 {options.number} 条)，下载已有的结果")

    os.makedirs(options.output_dir, exist_ok=True)
    print(f"\n开始下载 ({len(results)} 首)...")
    success = 0
    fail = 0
    skip = 0

    for index, song in enumerate(results):
        result = download_song(
            page,
            context,
            song,
            options.source,
            options.version,
            options.output_dir,
            index + 1,
            len(results),
            download_lyric=options.download_lyric,
            download_cover=options.download_cover,
            bitrate=options.bitrate,
        )
        if result == "success":
            success += 1
        elif result == "skip":
            skip += 1
        else:
            fail += 1
        if index < len(results) - 1:
            time.sleep(1)

    print(f"\n下载完成: 成功 {success} 首 / 失败 {fail} 首 / 跳过 {skip} 首")


def interactive_mode(page, context, version, args, script_dir):
    source = args.source
    search_type = args.search_type
    number = args.number
    save_dir = args.output_dir if args.output_dir else os.path.join(script_dir, "downloads")
    output_format = args.output_format

    print("\n=== 交互模式 ===")
    print("输入关键词搜索并下载，输入 q 退出")
    print("命令: s <来源> 切换音乐源 | n <数量> 修改数量 | so 只搜索不下载")
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
                print("  ✗ 无效来源: {}，可选: {}".format(new_source, ", ".join(VALID_SOURCES)))
            continue

        if user_input.lower().startswith("n ") and len(user_input) > 2:
            try:
                number = positive_int(user_input[2:].strip())
                print(f"  ✓ 数量已修改为: {number}")
            except argparse.ArgumentTypeError:
                print("  ✗ 无效数量，请输入正整数")
            continue

        search_only = user_input.lower() == "so"
        keyword = user_input if not search_only else ""
        if not keyword:
            try:
                keyword = input("关键词: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                continue
            if not keyword:
                continue

        options = RunOptions(
            keyword=keyword,
            source=source,
            search_type=search_type,
            number=number,
            output_dir=save_dir,
            output_format=output_format,
            search_only=search_only,
            select=False,
            download_lyric=not args.no_lyric,
            download_cover=not args.no_cover,
            bitrate=args.bitrate,
        )
        options.version = version
        do_search_and_download(page, context, options)
        print()


def import_playwright():
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("缺少运行依赖 playwright。请先运行: pip install -r requirements.txt")
        return None, None
    return sync_playwright, PlaywrightError


def run_with_browser(args, options):
    sync_playwright, playwright_error = import_playwright()
    if sync_playwright is None:
        return 1

    browser = None
    context = None
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    try:
        with sync_playwright() as playwright:
            print("正在访问页面，等待 Cloudflare 验证...")
            try:
                browser = playwright.chromium.launch(channel="chrome", headless=True)
            except playwright_error as exc:
                print(f"  ✗ 无法启动系统 Google Chrome: {exc}")
                print("  请确认已安装 Google Chrome，并可通过 Playwright channel='chrome' 启动。")
                return 1

            context = browser.new_context(user_agent=USER_AGENT)
            page = context.new_page()

            try:
                page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
            except Exception as exc:
                print(f"  ✗ 页面加载失败: {exc}")
                return 1

            cf_passed = wait_for_cloudflare(page)
            if not cf_passed:
                print("  ⚠ 无头模式未通过 Cloudflare 验证，尝试有头模式...")
                context.close()
                browser.close()
                browser = playwright.chromium.launch(channel="chrome", headless=False)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.goto(BASE_URL, wait_until="networkidle", timeout=60000)
                cf_passed = wait_for_cloudflare(page)

            if not cf_passed:
                print("  ✗ Cloudflare 验证未通过。请稍后重试，或在有头模式窗口中手动完成验证。")
                return 1

            version = page.evaluate("typeof mkPlayer !== 'undefined' ? mkPlayer.version : ''")
            if not version:
                print(f"  ⚠ 未能从页面获取 mkPlayer.version，使用默认值 {FALLBACK_VERSION}")
                version = FALLBACK_VERSION
            print(f"  ✓ 版本: {version}")

            if args.interactive:
                interactive_mode(page, context, version, args, script_dir)
            else:
                options.version = version
                do_search_and_download(page, context, options)
    finally:
        if context is not None:
            try:
                context.close()
            except Exception:
                pass
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass

    return 0


def main(argv=None):
    args = parse_args(argv)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    options = make_run_options(args, script_dir)
    return_code = run_with_browser(args, options)
    if return_code:
        sys.exit(return_code)
