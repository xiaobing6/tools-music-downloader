"""Typer CLI entrypoint."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Annotated

import typer

from music_downloader.core.config import (
    DEFAULT_BITRATE,
    DEFAULT_KEYWORD,
    DEFAULT_NUMBER,
    DEFAULT_SOURCE,
    SEARCH_TYPE_MAP,
    VALID_BITRATES,
    VALID_FORMATS,
    VALID_SOURCES,
)

if TYPE_CHECKING:
    from music_downloader.cli.models import RunOptions


def run_with_browser(options: RunOptions) -> int:
    from music_downloader.cli.workflow import run_with_browser as _run_with_browser

    return _run_with_browser(options)


def check_environment() -> int:
    from music_downloader.infrastructure.environment import check_environment as _check_environment

    return _check_environment()


def _value_list(values: list[str] | tuple[str, ...]) -> str:
    return " / ".join(values)


HELP_EPILOG = "\n\n".join(
    [
        "可选值:",
        f"--source   {_value_list(VALID_SOURCES)}",
        f"--type     {_value_list(tuple(SEARCH_TYPE_MAP))}",
        f"--format   {_value_list(VALID_FORMATS)}",
        f"--bitrate  {_value_list(VALID_BITRATES)}",
        "示例:",
        'python music_download.py -k "周杰伦" --source migu --search-only',
        'python music_download.py -k "Beyond" --type album --format list',
    ]
)


app = typer.Typer(
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
    help="music.gdstudio.org 音乐搜索与下载工具",
    epilog=HELP_EPILOG,
    rich_markup_mode="rich",
)


@app.callback(invoke_without_command=True)
def main_command(
    keyword: Annotated[str, typer.Option("-k", "--keyword", help="搜索关键词")] = DEFAULT_KEYWORD,
    source: Annotated[
        str,
        typer.Option("-s", "--source", help="音乐源，完整列表见下方"),
    ] = DEFAULT_SOURCE,
    number: Annotated[
        int, typer.Option("-n", "--number", min=1, help="获取结果总数")
    ] = DEFAULT_NUMBER,
    search_type: Annotated[
        str,
        typer.Option("-t", "--type", help="搜索类型，完整列表见下方"),
    ] = "song",
    output_dir: Annotated[
        str, typer.Option("-o", "--output", help="下载目录，默认使用项目 downloads/")
    ] = "",
    output_format: Annotated[
        str, typer.Option("-f", "--format", help="输出格式，完整列表见下方")
    ] = "table",
    bitrate: Annotated[
        str, typer.Option("-b", "--bitrate", help="音质选择，完整列表见下方")
    ] = DEFAULT_BITRATE,
    search_only: Annotated[bool, typer.Option("--search-only", help="只搜索不下载")] = False,
    select: Annotated[bool, typer.Option("--select", help="搜索后选择要下载的歌曲")] = False,
    no_lyric: Annotated[bool, typer.Option("--no-lyric", help="不下载歌词")] = False,
    no_cover: Annotated[bool, typer.Option("--no-cover", help="不嵌入封面")] = False,
    check_env: Annotated[
        bool, typer.Option("--check-env", help="检查本地依赖和 Google Chrome")
    ] = False,
    interactive: Annotated[bool, typer.Option("-i", "--interactive", help="交互模式")] = False,
    gui: Annotated[bool, typer.Option("--gui", help="启动桌面图形界面")] = False,
    user_data_dir: Annotated[
        str | None,
        typer.Option(
            "--user-data-dir", help="自定义 Chrome 用户数据目录，默认使用项目 .chrome-profile/"
        ),
    ] = None,
) -> None:
    if check_env:
        raise typer.Exit(check_environment())
    if gui:
        from music_downloader.gui.app import run_gui

        run_gui()
        return

    options = _build_run_options(
        keyword,
        source,
        number,
        search_type,
        output_dir,
        output_format,
        bitrate,
        search_only,
        select,
        no_lyric,
        no_cover,
        interactive,
        user_data_dir,
    )
    code = run_with_browser(options)
    if code:
        raise typer.Exit(code)


def _validate_choice(value: str, option_name: str, choices: list[str] | tuple[str, ...]) -> str:
    if value not in choices:
        raise typer.BadParameter(f"{option_name} 不支持 {value!r}，可选: {', '.join(choices)}")
    return value


def _build_run_options(
    keyword: str,
    source: str,
    number: int,
    search_type: str,
    output_dir: str,
    output_format: str,
    bitrate: str,
    search_only: bool,
    select: bool,
    no_lyric: bool,
    no_cover: bool,
    interactive: bool,
    user_data_dir: str | None,
) -> RunOptions:
    from music_downloader.cli.models import RunOptions

    return RunOptions(
        keyword=keyword,
        source=_validate_choice(source, "--source", VALID_SOURCES),
        search_type=_validate_choice(search_type, "--type", tuple(SEARCH_TYPE_MAP)),
        number=number,
        output_dir=output_dir,
        output_format=_validate_choice(output_format, "--format", VALID_FORMATS),
        search_only=search_only,
        select=select,
        download_lyric=not no_lyric,
        download_cover=not no_cover,
        bitrate=_validate_choice(bitrate, "--bitrate", VALID_BITRATES),
        interactive=interactive,
        user_data_dir=user_data_dir,
    )


def main(argv: list[str] | None = None) -> None:
    if argv is None and len(sys.argv) <= 1:
        from music_downloader.gui.app import run_gui

        run_gui()
        return
    app(args=argv, standalone_mode=True)
