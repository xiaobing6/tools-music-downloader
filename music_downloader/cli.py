"""Compatibility entrypoint for the Typer CLI adapter."""

from __future__ import annotations

from collections.abc import Sequence

from music_downloader.adapters.cli.app import app
from music_downloader.adapters.cli.app import main as _main
from music_downloader.adapters.cli.legacy import (
    build_interactive_options,
    do_search_and_download,
    fetch_player_version,
    import_playwright,
    interactive_mode,
    make_run_options,
    parse_args,
    parse_interactive_command,
    positive_int,
    run_with_browser,
)

__all__ = [
    "app",
    "build_interactive_options",
    "do_search_and_download",
    "fetch_player_version",
    "import_playwright",
    "interactive_mode",
    "make_run_options",
    "parse_args",
    "parse_interactive_command",
    "positive_int",
    "run_with_browser",
]


def main(argv: Sequence[str] | None = None) -> None:
    _main(list(argv) if argv is not None else None)
