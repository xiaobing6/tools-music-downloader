"""命令行参数解析、交互模式与主流程。"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
)

from music_downloader.api import wait_for_cloudflare
from music_downloader.config import (
    BASE_URL,
    DEFAULT_BITRATE,
    DEFAULT_KEYWORD,
    DEFAULT_NUMBER,
    DEFAULT_SOURCE,
    FALLBACK_VERSION,
    INTER_SONG_DELAY_SEC,
    PAGE_NAV_TIMEOUT_MS,
    SEARCH_TYPE_MAP,
    USER_AGENT,
    VALID_BITRATES,
    VALID_FORMATS,
    VALID_SOURCES,
)
from music_downloader.console import console
from music_downloader.display import display_results
from music_downloader.domain.enums import Bitrate, DownloadStatus, SearchType, Source
from music_downloader.domain.models import DownloadOptions, SearchOptions
from music_downloader.downloader import download_song
from music_downloader.env import check_environment
from music_downloader.infrastructure.gdstudio import GdStudioClient
from music_downloader.models import RunOptions
from music_downloader.services.search import SearchService
from music_downloader.utils import parse_selection, sanitize_filename

# 交互模式命令字面量
SET_SOURCE_PREFIX = "s "
SET_NUMBER_PREFIX = "n "
SEARCH_ONLY_TOKEN = "so"
QUIT_TOKEN = "q"


@dataclass
class InteractiveCommand:
    """解析后的交互模式单次输入。"""

    kind: str  # "search" | "search_only" | "set_source" | "set_number" | "quit"
    value: str = ""


def positive_int(value: str) -> int:
    """argparse 类型函数：验证值为正整数。"""
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是大于 0 的整数") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("必须是大于 0 的整数")
    return parsed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """解析命令行参数。

    Args:
        argv: 参数列表，默认使用 sys.argv[1:]。

    Returns:
        解析后的 argparse.Namespace。
    """
    parser = argparse.ArgumentParser(
        description="music.gdstudio.org 音乐搜索与下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage="%(prog)s [-k KEYWORD] [options]",
        epilog="""示例:
  %(prog)s -k "周杰伦"                 # 搜索并下载
  %(prog)s -k "Beyond" -n 5            # 限制下载数量
  %(prog)s -k "Beyond" -t album        # 搜索专辑
  %(prog)s -k "Beyond" -o "D:\\Music"   # 指定下载目录
  %(prog)s -k "Beyond" --search-only   # 仅搜索
  %(prog)s --check-env                 # 检查环境
  %(prog)s -i                          # 交互模式""",
    )

    # ── 搜索选项 ──
    search_group = parser.add_argument_group("搜索选项")
    search_group.add_argument(
        "-k", "--keyword", default=DEFAULT_KEYWORD, help=f"搜索关键词 (默认: {DEFAULT_KEYWORD})"
    )
    search_group.add_argument(
        "-s",
        "--source",
        default=DEFAULT_SOURCE,
        choices=VALID_SOURCES,
        help=f"音乐源 (默认: {DEFAULT_SOURCE})",
    )
    search_group.add_argument(
        "-n",
        "--number",
        type=positive_int,
        default=DEFAULT_NUMBER,
        help=f"获取结果总数 (默认: {DEFAULT_NUMBER}, 自动分页)",
    )
    search_group.add_argument(
        "-t",
        "--type",
        default="song",
        choices=SEARCH_TYPE_MAP.keys(),
        dest="search_type",
        help="搜索类型: song/album/playlist (默认: song)",
    )
    search_group.add_argument(
        "-f",
        "--format",
        default="table",
        choices=VALID_FORMATS,
        dest="output_format",
        help="输出格式 (默认: table)",
    )
    search_group.add_argument("--search-only", action="store_true", help="只搜索不下载")
    search_group.add_argument("--select", action="store_true", help="搜索后选择要下载的歌曲")

    # ── 下载选项 ──
    download_group = parser.add_argument_group("下载选项")
    download_group.add_argument(
        "-o",
        "--output",
        default="",
        dest="output_dir",
        help="下载目录 (默认: 脚本同级 downloads/, 会再自动按关键词建子目录)",
    )
    download_group.add_argument(
        "-b",
        "--bitrate",
        default=DEFAULT_BITRATE,
        choices=VALID_BITRATES,
        help=f"音质选择: 128/192/320/flac (默认: {DEFAULT_BITRATE})",
    )
    download_group.add_argument("--no-lyric", action="store_true", help="不下载歌词 (默认下载)")
    download_group.add_argument("--no-cover", action="store_true", help="不嵌入封面 (默认嵌入)")

    # ── 高级选项 ──
    advanced_group = parser.add_argument_group("高级选项")
    advanced_group.add_argument(
        "--check-env", action="store_true", help="检查本地依赖和 Google Chrome, 不访问音乐站点"
    )
    advanced_group.add_argument(
        "-i", "--interactive", action="store_true", help="交互模式, 浏览器保持运行可反复搜索"
    )
    advanced_group.add_argument("--gui", action="store_true", help="启动桌面图形界面")
    advanced_group.add_argument(
        "--user-data-dir",
        default=None,
        help="自定义 Chrome 用户数据目录 (默认在脚本同级 .chrome-profile/, 与系统 Chrome 隔离)",
    )
    return parser.parse_args(argv)


def make_run_options(args: argparse.Namespace, script_dir: str) -> RunOptions:
    """将 argparse 结果转换为 RunOptions 数据类。"""
    save_dir = os.path.abspath(
        args.output_dir if args.output_dir else os.path.join(script_dir, "downloads")
    )
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


def do_search_and_download(
    page: Any,
    context: Any,
    options: RunOptions,
    *,
    show_progress: bool = True,
) -> None:
    console.print(
        f'搜索 "{options.keyword}" (来源: {options.source}, 类型: {options.search_type}, 数量: {options.number})...',
        style="bold cyan",
    )
    client = GdStudioClient(page)
    songs = SearchService(client).search(
        SearchOptions(
            keyword=options.keyword,
            source=Source(options.source),
            search_type=SearchType(options.search_type),
            number=options.number,
        )
    )
    results = [song.to_legacy_dict() for song in songs]

    if not results:
        console.print("  未找到结果", style="yellow")
        return

    display_results(results, options.keyword, output_format=options.output_format)

    if options.search_only:
        return

    if options.select:
        try:
            selection = input(f"\n请选择要下载的歌曲 (如: 1,3,5-7，共 {len(results)} 首): ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            return
        if not selection:
            console.print("  未选择，跳过下载", style="yellow")
            return
        indices = parse_selection(
            selection,
            len(results),
            warn=lambda msg: console.print(msg, style="dim"),
        )
        if not indices:
            console.print("  无有效选择，跳过下载", style="yellow")
            return
        results = [results[index] for index in indices]
        console.print(f"  已选择 {len(results)} 首歌曲", style="green")

    if len(results) < options.number:
        console.print(
            f"\n实际找到 {len(results)} 条 (请求 {options.number} 条)，下载已有的结果",
            style="yellow",
        )

    target_dir = os.path.join(options.output_dir, sanitize_filename(options.keyword))
    os.makedirs(target_dir, exist_ok=True)
    download_options = DownloadOptions(
        source=Source(options.source),
        bitrate=Bitrate(options.bitrate),
        output_dir=Path(target_dir),
        download_lyric=options.download_lyric,
        download_cover=options.download_cover,
    )
    console.print(f"\n开始下载 ({len(results)} 首) -> {target_dir}", style="bold")
    success = 0
    fail = 0
    skip = 0

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        MofNCompleteColumn(),
        console=console,
        disable=not show_progress,
    ) as progress:
        task_id = progress.add_task(f"准备下载 {len(results)} 首", total=len(results))
        for index, song in enumerate(results):
            progress.update(
                task_id,
                description=f"第 {index + 1}/{len(results)} 首: {song.get('name', '?')}",
            )
            result = download_song(
                page,
                context,
                song,
                download_options.source.value,
                str(download_options.output_dir),
                index + 1,
                len(results),
                download_lyric=download_options.download_lyric,
                download_cover=download_options.download_cover,
                bitrate=download_options.bitrate.value,
            )
            try:
                status = DownloadStatus(result)
            except ValueError:
                status = DownloadStatus.FAIL
            if status == DownloadStatus.SUCCESS:
                success += 1
            elif status == DownloadStatus.SKIP:
                skip += 1
            else:
                fail += 1
            progress.advance(task_id)
            if index < len(results) - 1:
                time.sleep(INTER_SONG_DELAY_SEC)

    console.print(
        f"\n下载完成: 成功 {success} 首 / 失败 {fail} 首 / 跳过 {skip} 首",
        style="bold green" if fail == 0 else "bold yellow",
    )


def parse_interactive_command(text: str) -> InteractiveCommand | None:
    """纯函数：从用户输入解析为 InteractiveCommand。

    返回 None 表示空输入，跳过本轮。
    """
    stripped = text.strip()
    if not stripped:
        return None
    lowered = stripped.lower()
    if lowered == QUIT_TOKEN:
        return InteractiveCommand(kind="quit")
    if lowered.startswith(SET_SOURCE_PREFIX) and len(stripped) > len(SET_SOURCE_PREFIX):
        return InteractiveCommand(
            kind="set_source",
            value=stripped[len(SET_SOURCE_PREFIX) :].strip(),
        )
    if lowered.startswith(SET_NUMBER_PREFIX) and len(stripped) > len(SET_NUMBER_PREFIX):
        return InteractiveCommand(
            kind="set_number",
            value=stripped[len(SET_NUMBER_PREFIX) :].strip(),
        )
    if lowered == SEARCH_ONLY_TOKEN:
        return InteractiveCommand(kind="search_only")
    return InteractiveCommand(kind="search", value=stripped)


def build_interactive_options(
    cmd: InteractiveCommand,
    base: argparse.Namespace,
    state: dict,
    save_dir: str,
) -> RunOptions | None:
    """根据 interactive 内部状态和命令构造 RunOptions。

    返回 None 表示用户取消（Ctrl-C / EOF） 或未输入关键词。
    """
    keyword = cmd.value if cmd.kind == "search" else ""
    if not keyword and cmd.kind in ("search", "search_only"):
        try:
            keyword = input("关键词: ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
    if not keyword and cmd.kind in ("search", "search_only"):
        return None
    return RunOptions(
        keyword=keyword,
        source=state["source"],
        search_type=state["search_type"],
        number=state["number"],
        output_dir=save_dir,
        output_format=state["output_format"],
        search_only=cmd.kind == "search_only",
        select=False,
        download_lyric=not base.no_lyric,
        download_cover=not base.no_cover,
        bitrate=base.bitrate,
    )


def interactive_mode(
    page: Any,
    context: Any,
    args: argparse.Namespace,
    script_dir: str,
) -> None:
    state = {
        "source": args.source,
        "search_type": args.search_type,
        "number": args.number,
        "output_format": args.output_format,
    }
    save_dir = os.path.abspath(
        args.output_dir if args.output_dir else os.path.join(script_dir, "downloads")
    )

    console.print("\n=== 交互模式 ===", style="bold")
    console.print("输入关键词搜索并下载，输入 q 退出")
    console.print("命令: s <来源> 切换音乐源 | n <数量> 修改数量 | so 只搜索不下载")
    console.print(
        f"当前设置: 来源={state['source']}, 类型={state['search_type']}, 数量={state['number']}"
    )
    console.print()

    while True:
        try:
            user_input = input("搜索: ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n退出")
            return

        cmd = parse_interactive_command(user_input)
        if cmd is None:
            continue
        if cmd.kind == "quit":
            console.print("退出")
            return
        if cmd.kind == "set_source":
            if cmd.value in VALID_SOURCES:
                state["source"] = cmd.value
                console.print(f"  ✓ 音乐源已切换为: {state['source']}", style="green")
            else:
                console.print(
                    f"  ✗ 无效来源: {cmd.value}，可选: {', '.join(VALID_SOURCES)}",
                    style="red",
                )
            continue
        if cmd.kind == "set_number":
            try:
                state["number"] = positive_int(cmd.value)
                console.print(f"  ✓ 数量已修改为: {state['number']}", style="green")
            except argparse.ArgumentTypeError:
                console.print("  ✗ 无效数量，请输入正整数", style="red")
            continue

        options = build_interactive_options(cmd, args, state, save_dir)
        if options is None:
            continue
        do_search_and_download(page, context, options, show_progress=False)
        console.print()


def import_playwright() -> tuple[Any, Any]:
    """延迟导入 playwright，失败时打印提示并返回 (None, None)。"""
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError:
        console.print(
            "缺少运行依赖 playwright。请先运行: pip install -r requirements.txt",
            style="red",
        )
        return None, None
    return sync_playwright, PlaywrightError


def fetch_player_version(
    page: Any,
    fallback: str = FALLBACK_VERSION,
) -> str:
    """从页面获取 mkPlayer.version，失败时使用回退值。"""
    version = page.evaluate("typeof mkPlayer !== 'undefined' ? mkPlayer.version : ''")
    if not version:
        console.print(
            f"  ⚠ 未能从页面获取 mkPlayer.version，使用默认值 {fallback}",
            style="yellow",
        )
        return fallback
    return version


def _open_browser(
    playwright: Any,
    *,
    headless: bool,
    user_agent: str,
    user_data_dir: str,
) -> Any:
    """启动一个持久化 context 浏览器。

    与 launch + new_context 的区别：persistent context 自带 user_data_dir，
    cf_clearance 等 cookie 在多次运行间复用，且不会污染用户系统 Chrome profile。
    返回值即 context，page 需用 context.pages[0] 或 context.new_page() 获取。
    """
    return playwright.chromium.launch_persistent_context(
        user_data_dir=user_data_dir,
        channel="chrome",
        headless=headless,
        user_agent=user_agent,
    )


def _resolve_user_data_dir(args: argparse.Namespace, script_dir: str) -> str:
    """根据 CLI 参数决定 user_data_dir。

    用户显式 --user-data-dir 时用用户路径；否则统一用脚本同级的
    .chrome-profile/（与系统 Chrome 隔离）。
    """
    if args.user_data_dir:
        return os.path.abspath(args.user_data_dir)
    return os.path.abspath(os.path.join(script_dir, ".chrome-profile"))


def run_with_browser(args: argparse.Namespace) -> int:
    """主流程：启动浏览器、通过 Cloudflare 验证、执行搜索/下载或交互模式。

    Args:
        args: parse_args 的返回值。

    Returns:
        退出码，0 表示成功，非 0 表示失败。
    """
    sync_playwright, playwright_error = import_playwright()
    if sync_playwright is None:
        return 1

    if "__compiled__" in globals():
        # Nuitka 编译环境：sys.argv[0] 是用户执行的真实 EXE 路径
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        # 源码环境：__file__ 是 cli.py 的路径，需要向上两层到项目根目录
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    user_data_dir = _resolve_user_data_dir(args, script_dir)
    os.makedirs(user_data_dir, exist_ok=True)
    console.print(f"  ✓ Chrome 用户数据目录: {user_data_dir}", style="dim")

    context: Any = None

    try:
        with sync_playwright() as playwright:
            console.print("正在访问页面，等待 Cloudflare 验证...", style="cyan")
            try:
                context = _open_browser(
                    playwright,
                    headless=True,
                    user_agent=USER_AGENT,
                    user_data_dir=user_data_dir,
                )
            except playwright_error as exc:
                console.print(f"  ✗ 无法启动系统 Google Chrome: {exc}", style="red")
                console.print(
                    "  请确认已安装 Google Chrome，并可通过 Playwright channel='chrome' 启动。"
                )
                return 1

            page = context.pages[0] if context.pages else context.new_page()

            try:
                page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
            except Exception as exc:
                console.print(f"  ✗ 页面加载失败: {exc}", style="red")
                return 1

            cf_passed = wait_for_cloudflare(page)
            if not cf_passed:
                console.print(
                    "  ⚠ 无头模式未通过 Cloudflare 验证，尝试有头模式...",
                    style="yellow",
                )
                with contextlib.suppress(Exception):
                    context.close()
                context = _open_browser(
                    playwright,
                    headless=False,
                    user_agent=USER_AGENT,
                    user_data_dir=user_data_dir,
                )
                page = context.pages[0] if context.pages else context.new_page()
                page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
                cf_passed = wait_for_cloudflare(page)

            if not cf_passed:
                console.print(
                    "  ✗ Cloudflare 验证未通过。请稍后重试，或在有头模式窗口中手动完成验证。",
                    style="red",
                )
                return 1

            version = fetch_player_version(page)
            console.print(f"  ✓ 版本: {version}", style="green")

            options = make_run_options(args, script_dir)

            if args.interactive:
                interactive_mode(page, context, args, script_dir)
            else:
                do_search_and_download(page, context, options)
    finally:
        # launch_persistent_context 返回的 context 本身关闭时即关闭浏览器进程
        if context is not None:
            with contextlib.suppress(Exception):
                context.close()

    return 0


def legacy_main(argv: Sequence[str] | None = None) -> None:
    """程序入口：解析参数后执行环境检查、GUI 或 CLI 主流程。"""
    args = parse_args(argv)
    if args.check_env:
        sys.exit(check_environment())

    # GUI 模式：显式 --gui 标志，或无任何命令行参数时（双击 exe/直接运行脚本）
    is_gui_mode = args.gui or (argv is None and len(sys.argv) <= 1)
    if is_gui_mode:
        from music_downloader.gui.app import run_gui

        run_gui()
        return

    return_code = run_with_browser(args)
    if return_code:
        sys.exit(return_code)
