import subprocess
import sys

from music_downloader.cli import parse_args


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
