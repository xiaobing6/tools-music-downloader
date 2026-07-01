from __future__ import annotations

from music_downloader.infrastructure.environment import EnvironmentCheck, run_environment_checks


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
