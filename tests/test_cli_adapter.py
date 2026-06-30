from __future__ import annotations

from typer.testing import CliRunner

from music_downloader.adapters.cli.app import app
from music_downloader.adapters.cli.interactive import parse_interactive_command


def test_help_includes_existing_options() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "--keyword" in result.output
    assert "--search-only" in result.output
    assert "--gui" in result.output


def test_short_help_option_works() -> None:
    result = CliRunner().invoke(app, ["-h"])

    assert result.exit_code == 0
    assert "--keyword" in result.output


def test_interactive_parser_keeps_existing_commands() -> None:
    assert parse_interactive_command("q").kind == "quit"
    assert parse_interactive_command("s netease").kind == "set_source"
    assert parse_interactive_command("n 10").kind == "set_number"
    assert parse_interactive_command("so").kind == "search_only"
