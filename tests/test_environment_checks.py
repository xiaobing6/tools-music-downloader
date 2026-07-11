from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from music_downloader.infrastructure.environment import (
    EnvironmentCheck,
    check_python_version,
    run_environment_checks,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    ("version_info", "expected_ok"),
    [((3, 10, 99), False), ((3, 11, 0), True)],
)
def test_python_version_requires_3_11(
    version_info: tuple[int, int, int], expected_ok: bool
) -> None:
    check = check_python_version(version_info)

    assert check.ok is expected_ok
    if not expected_ok:
        assert "需要 Python 3.11+" in check.detail


def test_tooling_configuration_targets_python_3_11() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert config["project"]["requires-python"] == ">=3.11"
    assert config["tool"]["ruff"]["target-version"] == "py311"
    assert config["tool"]["mypy"]["python_version"] == "3.11"


def test_environment_checks_accept_fake_chrome_checker() -> None:
    def fake_chrome() -> EnvironmentCheck:
        return EnvironmentCheck("Google Chrome", True, "fake ok")

    checks = run_environment_checks(chrome_checker=fake_chrome)

    assert checks[-1].name == "Google Chrome"
    assert checks[-1].ok is True


def test_environment_checks_do_not_require_removed_rich_argparse() -> None:
    checks = run_environment_checks(
        chrome_checker=lambda: EnvironmentCheck("Google Chrome", True, "ok")
    )

    assert "rich-argparse" not in {check.name for check in checks}
