import sys

from music_downloader import env


def test_check_python_version_passes_for_supported_version():
    result = env.check_python_version((3, 8, 0))

    assert result.ok is True


def test_check_python_version_fails_for_old_version():
    result = env.check_python_version((3, 7, 9))

    assert result.ok is False


def test_run_environment_checks_reports_failed_module(monkeypatch):
    def fake_find_spec(module_name):
        if module_name == "mutagen":
            return None
        return object()

    monkeypatch.setattr(env.importlib.util, "find_spec", fake_find_spec)

    checks = env.run_environment_checks(
        chrome_checker=lambda: env.EnvironmentCheck("Google Chrome", True, "ok")
    )

    failed = [check.name for check in checks if not check.ok]
    assert failed == ["mutagen"]


def test_check_environment_returns_failure_for_failed_check(monkeypatch):
    monkeypatch.setattr(
        env,
        "run_environment_checks",
        lambda: [
            env.EnvironmentCheck("Python 版本", True, "ok"),
            env.EnvironmentCheck("Google Chrome", False, "no chrome"),
        ],
    )
    monkeypatch.setattr(env, "render_environment_checks", lambda checks: None)

    assert env.check_environment() == 1


def test_check_environment_returns_success_for_all_passed(monkeypatch):
    monkeypatch.setattr(
        env,
        "run_environment_checks",
        lambda: [
            env.EnvironmentCheck("Python 版本", True, "ok"),
            env.EnvironmentCheck("Google Chrome", True, "ok"),
        ],
    )
    monkeypatch.setattr(env, "render_environment_checks", lambda checks: None)

    assert env.check_environment() == 0


def test_check_env_cli_does_not_start_real_browser(monkeypatch):
    monkeypatch.setattr(
        env,
        "run_environment_checks",
        lambda: [env.EnvironmentCheck("Python 版本", True, sys.version.split()[0])],
    )
    monkeypatch.setattr(env, "render_environment_checks", lambda checks: None)

    assert env.check_environment() == 0


def test_render_environment_checks_falls_back_without_rich(monkeypatch, capsys):
    monkeypatch.setattr(env, "RichTable", None)

    env.render_environment_checks([env.EnvironmentCheck("rich", False, "missing")])

    captured = capsys.readouterr()
    assert "rich" in captured.out
    assert "missing" in captured.out
