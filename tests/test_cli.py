import argparse
import subprocess
import sys

import pytest

from music_downloader.cli import (
    InteractiveCommand,
    parse_args,
    parse_interactive_command,
    positive_int,
)


def test_help_works_without_runtime_dependencies():
    result = subprocess.run(
        [sys.executable, "music_download.py", "-h"],
        capture_output=True,
    )

    assert result.returncode == 0
    assert b"usage: music_download.py" in result.stdout


def test_module_help_uses_same_cli():
    result = subprocess.run(
        [sys.executable, "-m", "music_downloader", "-h"],
        capture_output=True,
    )

    assert result.returncode == 0
    assert b"--check-env" in result.stdout


def test_number_must_be_positive():
    result = subprocess.run(
        [sys.executable, "music_download.py", "-n", "0", "--search-only"],
        capture_output=True,
    )

    assert result.returncode != 0
    assert b"-n" in result.stderr


def test_parse_args_keeps_existing_interface():
    args = parse_args(["-k", "Beyond", "-s", "netease", "-n", "1", "--search-only"])

    assert args.keyword == "Beyond"
    assert args.source == "netease"
    assert args.number == 1
    assert args.search_only is True


def test_parse_args_supports_new_options():
    args = parse_args(
        [
            "--user-data-dir",
            "/tmp/profile",
            "--no-isolated-profile",
            "--mk-version",
            "2026.5.10",
        ]
    )

    assert args.user_data_dir == "/tmp/profile"
    assert args.no_isolated_profile is True
    assert args.mk_version == "2026.5.10"


def test_positive_int_rejects_zero_and_negative():
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int("0")
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int("-3")
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int("abc")


def test_positive_int_accepts():
    assert positive_int("1") == 1
    assert positive_int("42") == 42


# parse_interactive_command 覆盖


def test_parse_interactive_command_empty():
    assert parse_interactive_command("") is None
    assert parse_interactive_command("   ") is None


def test_parse_interactive_command_quit():
    assert parse_interactive_command("q") == InteractiveCommand(kind="quit")
    assert parse_interactive_command("Q") == InteractiveCommand(kind="quit")


def test_parse_interactive_command_set_source():
    cmd = parse_interactive_command("s netease")
    assert cmd is not None
    assert cmd.kind == "set_source"
    assert cmd.value == "netease"

    # 大小写不敏感
    cmd2 = parse_interactive_command("S Kuwo")
    assert cmd2 is not None
    assert cmd2.kind == "set_source"
    assert cmd2.value == "Kuwo"


def test_parse_interactive_command_set_number():
    cmd = parse_interactive_command("n 5")
    assert cmd is not None
    assert cmd.kind == "set_number"
    assert cmd.value == "5"


def test_parse_interactive_command_search_only():
    assert parse_interactive_command("so") == InteractiveCommand(kind="search_only")
    assert parse_interactive_command("SO") == InteractiveCommand(kind="search_only")


def test_parse_interactive_command_search_keyword():
    cmd = parse_interactive_command("周杰伦")
    assert cmd is not None
    assert cmd.kind == "search"
    assert cmd.value == "周杰伦"

    # "s" 单独出现不是 set_source 命令（prefix 需要空格）
    cmd2 = parse_interactive_command("s")
    assert cmd2 is not None
    assert cmd2.kind == "search"
    assert cmd2.value == "s"
