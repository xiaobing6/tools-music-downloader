from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "music_downloader"


def test_root_package_only_contains_package_entry_modules() -> None:
    allowed = {"__init__.py", "__main__.py"}
    root_modules = {path.name for path in ROOT.glob("*.py")}

    assert root_modules == allowed


def test_cli_and_gui_are_sibling_interface_packages() -> None:
    package_dirs = {path.name for path in ROOT.iterdir() if path.is_dir()}

    assert "cli" in package_dirs
    assert "core" in package_dirs
    assert "gui" in package_dirs
    assert "adapters" not in package_dirs
    assert not (ROOT / "cli" / "legacy.py").exists()


def test_shared_config_and_console_live_in_core_package() -> None:
    assert (ROOT / "core" / "config.py").is_file()
    assert (ROOT / "core" / "console.py").is_file()
    assert not (ROOT / "config.py").exists()
    assert not (ROOT / "console.py").exists()
