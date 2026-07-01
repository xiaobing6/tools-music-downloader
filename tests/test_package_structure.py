from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "music_downloader"


def test_root_package_only_contains_entry_config_and_console_modules() -> None:
    allowed = {"__init__.py", "__main__.py", "config.py", "console.py"}
    root_modules = {path.name for path in ROOT.glob("*.py")}

    assert root_modules == allowed
