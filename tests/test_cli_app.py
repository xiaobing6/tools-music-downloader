from __future__ import annotations

from typer.testing import CliRunner

from music_downloader.cli.app import app
from music_downloader.cli.interactive import parse_interactive_command
from music_downloader.core.config import (
    SEARCH_TYPE_MAP,
    VALID_BITRATES,
    VALID_FORMATS,
    VALID_SOURCES,
)


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


def test_help_lists_supported_option_values() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    for value in VALID_SOURCES:
        assert value in result.output
    for value in SEARCH_TYPE_MAP:
        assert value in result.output
    for value in VALID_FORMATS:
        assert value in result.output
    for value in VALID_BITRATES:
        assert value in result.output
    assert "downloads" in result.output
    assert ".chrome-profile" in result.output


def test_help_uses_rich_rendering() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "┌─ Options" in result.output
    assert "mig…" not in result.output


def test_interactive_parser_keeps_existing_commands() -> None:
    assert parse_interactive_command("q").kind == "quit"
    assert parse_interactive_command("s netease").kind == "set_source"
    assert parse_interactive_command("n 10").kind == "set_number"
    assert parse_interactive_command("so").kind == "search_only"
