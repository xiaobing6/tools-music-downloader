"""本地环境检查：Python 版本、依赖模块、Google Chrome 可用性。"""

from __future__ import annotations

import contextlib
import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from music_downloader.console import PlainConsole, RichTable, console


@dataclass
class EnvironmentCheck:
    """单项环境检查结果。"""

    name: str
    ok: bool
    detail: str


def check_python_version(
    version_info: tuple[int, int, int] = sys.version_info[:3],
) -> EnvironmentCheck:
    """检查 Python 版本是否 >= 3.10。"""
    ok = version_info >= (3, 10, 0)
    version = ".".join(str(part) for part in version_info)
    detail = f"Python {version}" if ok else f"需要 Python 3.10+，当前为 Python {version}"
    return EnvironmentCheck("Python 版本", ok, detail)


def check_module(module_name: str, package_name: str | None = None) -> EnvironmentCheck:
    """检查指定 Python 模块是否已安装。"""
    package = package_name or module_name
    if importlib.util.find_spec(module_name) is None:
        return EnvironmentCheck(package, False, "未安装，请运行: pip install -r requirements.txt")
    return EnvironmentCheck(package, True, "已安装")


def check_chrome_launcher(
    sync_playwright_factory: Callable[[], Any] | None = None,
) -> EnvironmentCheck:
    """尝试通过 Playwright channel='chrome' 启动 Google Chrome。

    Args:
        sync_playwright_factory: 可选的 sync_playwright 工厂函数，用于测试注入。

    Returns:
        检查结果，包含是否可启动及错误信息。
    """
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
    """依次执行所有环境检查并返回结果列表。"""
    checks = [
        check_python_version(),
        check_module("playwright"),
        check_module("mutagen"),
        check_module("rich"),
        check_module("rich_argparse", "rich-argparse"),
        check_module("webview", "pywebview"),
    ]
    checker = chrome_checker or check_chrome_launcher
    checks.append(checker())
    return checks


def render_environment_checks(checks: list[EnvironmentCheck]) -> None:
    """将环境检查结果渲染为表格或纯文本输出。"""
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
    """执行完整环境检查并输出结果，全部通过返回 0 否则返回 1。"""
    checks = run_environment_checks()
    render_environment_checks(checks)
    return 0 if all(check.ok for check in checks) else 1
