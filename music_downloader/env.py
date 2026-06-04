import contextlib
import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .console import PlainConsole, RichTable, console


@dataclass
class EnvironmentCheck:
    name: str
    ok: bool
    detail: str


def check_python_version(
    version_info: tuple[int, int, int] = sys.version_info[:3],
) -> EnvironmentCheck:
    ok = version_info >= (3, 8, 0)
    version = ".".join(str(part) for part in version_info)
    detail = f"Python {version}" if ok else f"需要 Python 3.8+，当前为 Python {version}"
    return EnvironmentCheck("Python 版本", ok, detail)


def check_module(module_name: str, package_name: str | None = None) -> EnvironmentCheck:
    package = package_name or module_name
    if importlib.util.find_spec(module_name) is None:
        return EnvironmentCheck(package, False, "未安装，请运行: pip install -r requirements.txt")
    return EnvironmentCheck(package, True, "已安装")


def check_chrome_launcher(
    sync_playwright_factory: Callable[[], Any] | None = None,
) -> EnvironmentCheck:
    try:
        if sync_playwright_factory is None:
            from playwright.sync_api import sync_playwright

            sync_playwright_factory = sync_playwright
    except ImportError:
        return EnvironmentCheck("Google Chrome", False, "无法检查：playwright 未安装")

    browser = None
    try:
        with sync_playwright_factory() as playwright:
            browser = playwright.chromium.launch(channel="chrome", headless=True)
            return EnvironmentCheck(
                "Google Chrome", True, "可通过 Playwright channel='chrome' 启动"
            )
    except Exception as exc:
        return EnvironmentCheck("Google Chrome", False, f"无法启动系统 Chrome: {exc}")
    finally:
        if browser is not None:
            with contextlib.suppress(Exception):
                browser.close()


def run_environment_checks(
    chrome_checker: Callable[[], EnvironmentCheck] | None = None,
) -> list[EnvironmentCheck]:
    checks = [
        check_python_version(),
        check_module("playwright"),
        check_module("mutagen"),
        check_module("rich"),
    ]
    checker = chrome_checker or check_chrome_launcher
    checks.append(checker())
    return checks


def render_environment_checks(checks: list[EnvironmentCheck]) -> None:
    if RichTable is None:
        # Use a PlainConsole so the output goes straight to sys.stdout
        # (and is therefore captured by tests via capsys).
        fallback = PlainConsole()
        fallback.print("环境检查")
        for check in checks:
            status = "通过" if check.ok else "失败"
            fallback.print(f"- {check.name}: {status} - {check.detail}")
        return

    table = RichTable(title="环境检查")
    table.add_column("项目", style="cyan")
    table.add_column("状态")
    table.add_column("说明")

    for check in checks:
        status = "[green]通过[/green]" if check.ok else "[red]失败[/red]"
        table.add_row(check.name, status, check.detail)

    console.print(table)


def check_environment() -> int:
    checks = run_environment_checks()
    render_environment_checks(checks)
    return 0 if all(check.ok for check in checks) else 1
