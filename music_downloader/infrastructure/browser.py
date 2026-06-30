"""Shared Playwright browser session management."""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from typing import Any

from music_downloader.config import BASE_URL, PAGE_NAV_TIMEOUT_MS, USER_AGENT
from music_downloader.domain.errors import BrowserStartupError, CloudflareError
from music_downloader.infrastructure.gdstudio import wait_for_cloudflare


def runtime_root() -> Path:
    if "__compiled__" in globals():
        return Path(os.path.abspath(sys.argv[0])).parent
    return Path(__file__).resolve().parents[2]


def default_user_data_dir() -> Path:
    return runtime_root() / ".chrome-profile"


class BrowserSession:
    def __init__(self, *, user_data_dir: str | os.PathLike[str] | None = None, headless: bool = True):
        self.user_data_dir = Path(user_data_dir) if user_data_dir else default_user_data_dir()
        self.headless = headless
        self._playwright_cm: Any = None
        self._playwright: Any = None
        self.context: Any = None
        self.page: Any = None

    def __enter__(self) -> BrowserSession:
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserStartupError(
                "缺少运行依赖 playwright。请先运行: pip install -r requirements.txt"
            ) from exc

        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._playwright_cm = sync_playwright()
        self._playwright = self._playwright_cm.start()
        try:
            self.context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                channel="chrome",
                headless=self.headless,
                user_agent=USER_AGENT,
            )
        except Exception as exc:
            self.close()
            raise BrowserStartupError(f"无法启动系统 Google Chrome: {exc}") from exc
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        try:
            self.page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
            if not wait_for_cloudflare(self.page):
                raise CloudflareError("Cloudflare 验证未通过")
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        with contextlib.suppress(Exception):
            if self.context is not None:
                self.context.close()
        with contextlib.suppress(Exception):
            if self._playwright_cm is not None:
                self._playwright_cm.stop()
        self.context = None
        self.page = None
