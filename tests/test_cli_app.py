from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

import music_downloader.cli.app as cli_app_module
from music_downloader.cli import workflow
from music_downloader.cli.app import app
from music_downloader.cli.interactive import parse_interactive_command
from music_downloader.cli.models import RunOptions
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


def test_help_lists_source_ids_with_display_names() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "netease（网易云音乐）" in result.output
    assert "kugou（酷狗音乐）" in result.output


def test_help_uses_rich_rendering() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "┌─ Options" in result.output
    assert "mig…" not in result.output


def test_cli_app_import_does_not_load_runtime_modules_for_help() -> None:
    code = (
        "import sys\n"
        "import music_downloader.cli.app\n"
        "runtime_modules = [\n"
        "    'music_downloader.cli.workflow',\n"
        "    'music_downloader.cli.models',\n"
        "    'music_downloader.infrastructure.environment',\n"
        "]\n"
        "loaded = [name for name in runtime_modules if name in sys.modules]\n"
        "print('\\n'.join(loaded))\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""


def test_interactive_parser_keeps_existing_commands() -> None:
    assert parse_interactive_command("q").kind == "quit"
    assert parse_interactive_command("s netease").kind == "set_source"
    assert parse_interactive_command("n 10").kind == "set_number"
    assert parse_interactive_command("so").kind == "search_only"


def test_main_command_passes_run_options_without_argparse(monkeypatch) -> None:
    captured: dict[str, RunOptions] = {}

    def forbidden_parse_args(argv: list[str]) -> object:
        raise AssertionError(f"parse_args should not be called: {argv}")

    def fake_run_with_browser(options: RunOptions) -> int:
        captured["options"] = options
        return 0

    monkeypatch.setattr(cli_app_module, "parse_args", forbidden_parse_args, raising=False)
    monkeypatch.setattr(cli_app_module, "run_with_browser", fake_run_with_browser)

    result = CliRunner().invoke(
        app,
        [
            "-k",
            "Beyond",
            "--source",
            "migu",
            "--number",
            "3",
            "--type",
            "album",
            "--output",
            "D:\\Music",
            "--format",
            "json",
            "--bitrate",
            "flac",
            "--search-only",
            "--select",
            "--no-lyric",
            "--no-cover",
            "--interactive",
            "--user-data-dir",
            "D:\\ChromeProfile",
        ],
    )

    assert result.exit_code == 0
    options = captured["options"]
    assert options == RunOptions(
        keyword="Beyond",
        source="migu",
        search_type="album",
        number=3,
        output_dir="D:\\Music",
        output_format="json",
        search_only=True,
        select=True,
        download_lyric=False,
        download_cover=False,
        bitrate="flac",
        interactive=True,
        user_data_dir="D:\\ChromeProfile",
    )


def test_invalid_cli_choices_do_not_start_browser(monkeypatch) -> None:
    def fail_run_with_browser(options: RunOptions) -> int:
        raise AssertionError(f"run_with_browser should not be called: {options}")

    monkeypatch.setattr(cli_app_module, "run_with_browser", fail_run_with_browser)

    result = CliRunner().invoke(app, ["--source", "missing"])

    assert result.exit_code != 0
    assert "missing" in result.output
    assert "netease" in result.output


def test_build_interactive_options_uses_run_options_base(tmp_path: Path) -> None:
    base = RunOptions(
        keyword="initial",
        source="netease",
        search_type="song",
        number=1,
        output_dir=str(tmp_path),
        output_format="table",
        search_only=False,
        select=True,
        download_lyric=False,
        download_cover=False,
        bitrate="flac",
        interactive=True,
        user_data_dir="D:\\ChromeProfile",
    )
    state = {
        "source": "migu",
        "search_type": "playlist",
        "number": 5,
        "output_format": "json",
    }

    options = workflow.build_interactive_options(
        workflow.InteractiveCommand(kind="search", value="新关键词"),
        base,
        state,
    )

    assert options == RunOptions(
        keyword="新关键词",
        source="migu",
        search_type="playlist",
        number=5,
        output_dir=str(tmp_path),
        output_format="json",
        search_only=False,
        select=False,
        download_lyric=False,
        download_cover=False,
        bitrate="flac",
        interactive=False,
        user_data_dir="D:\\ChromeProfile",
    )


def test_source_runtime_root_matches_entrypoint_directory() -> None:
    root = workflow._source_runtime_root(workflow.__file__)

    assert root == Path(__file__).resolve().parents[1]
    assert (root / "music_download.py").is_file()


def test_default_user_data_dir_uses_activated_recovery_profile(tmp_path: Path) -> None:
    profile_root = tmp_path / ".chrome-profile"
    profile_root.mkdir()
    (profile_root / ".active-profile").write_text("recovery", encoding="utf-8")

    resolved = workflow._resolve_user_data_dir(None, str(tmp_path))

    assert resolved == str((profile_root / "recovery").resolve())
