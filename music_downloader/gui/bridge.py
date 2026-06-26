"""Bridge layer between GUI and existing core modules.

Wraps Playwright browser lifecycle, search, and download operations
in a thread-safe manner suitable for GUI use. Long operations run on
background threads and emit events via callbacks.
"""

from __future__ import annotations

import contextlib
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from music_downloader.api import search_with_pagination, wait_for_cloudflare
from music_downloader.config import (
    BASE_URL,
    INTER_SONG_DELAY_SEC,
    PAGE_NAV_TIMEOUT_MS,
    USER_AGENT,
)
from music_downloader.downloader import download_song
from music_downloader.env import run_environment_checks
from music_downloader.utils import normalize_song, sanitize_filename

LogCallback = Callable[[str, str], None]
ProgressCallback = Callable[[dict[str, Any]], None]


@dataclass
class DownloadTask:
    task_id: str
    songs: list[dict[str, Any]]
    source: str
    bitrate: str
    download_lyric: bool
    download_cover: bool
    output_dir: str
    cancel_event: threading.Event = field(default_factory=threading.Event)
    success: int = 0
    fail: int = 0
    skip: int = 0


class BrowserSession:
    """Manages Playwright browser lifecycle for GUI use."""

    def __init__(self, on_log: LogCallback | None = None):
        self._playwright_cm = None
        self._playwright = None
        self._context = None
        self._page = None
        self._browser_ready = threading.Event()
        self._lock = threading.Lock()
        self._on_log = on_log
        self._cf_passed = False

    def _log(self, msg: str, level: str = "info") -> None:
        if self._on_log:
            self._on_log(msg, level)

    def _open_browser(self, playwright: Any, *, headless: bool, user_data_dir: str) -> Any:
        return playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            headless=headless,
            user_agent=USER_AGENT,
        )

    def start(self, headless: bool = True, user_data_dir: str | None = None) -> bool:
        """Start browser and pass Cloudflare. Returns True if ready."""
        if self._browser_ready.is_set():
            return True
        with self._lock:
            if self._browser_ready.is_set():
                return True
            try:
                from playwright.sync_api import sync_playwright
            except ImportError:
                self._log("缺少 playwright 依赖，请运行 pip install -r requirements.txt", "error")
                return False

            if user_data_dir is None:
                base_dir = os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                user_data_dir = os.path.join(base_dir, ".chrome-profile")
            os.makedirs(user_data_dir, exist_ok=True)

            try:
                self._playwright_cm = sync_playwright()
                self._playwright = self._playwright_cm.start()
                self._log("正在启动浏览器...", "info")
                self._context = self._open_browser(
                    self._playwright,
                    headless=headless,
                    user_data_dir=user_data_dir,
                )
                self._page = (
                    self._context.pages[0] if self._context.pages else self._context.new_page()
                )
                self._log("正在访问音乐站点，等待 Cloudflare 验证...", "info")
                self._page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
                self._cf_passed = wait_for_cloudflare(self._page)
                if not self._cf_passed and headless:
                    self._log("无头模式未通过验证，尝试有头模式...", "warn")
                    with contextlib.suppress(Exception):
                        self._context.close()
                    self._context = self._open_browser(
                        self._playwright,
                        headless=False,
                        user_data_dir=user_data_dir,
                    )
                    self._page = (
                        self._context.pages[0] if self._context.pages else self._context.new_page()
                    )
                    self._page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
                    self._cf_passed = wait_for_cloudflare(self._page)
                if self._cf_passed:
                    self._log("浏览器就绪，Cloudflare 验证通过", "success")
                    self._browser_ready.set()
                    return True
                self._log("Cloudflare 验证未通过", "error")
                return False
            except Exception as exc:
                self._log(f"浏览器启动失败: {exc}", "error")
                return False

    @property
    def page(self) -> Any:
        return self._page

    @property
    def context(self) -> Any:
        return self._context

    @property
    def ready(self) -> bool:
        return self._browser_ready.is_set()

    def stop(self) -> None:
        with self._lock:
            if self._context is not None:
                with contextlib.suppress(Exception):
                    self._context.close()
                self._context = None
            if self._playwright is not None:
                with contextlib.suppress(Exception):
                    self._playwright_cm.stop()
                self._playwright = None
                self._playwright_cm = None
            self._browser_ready.clear()
            self._cf_passed = False


class MusicBridge:
    """High-level bridge that GUI api.py calls into."""

    def __init__(
        self,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
    ):
        self._on_log = on_log
        self._on_progress = on_progress
        self._session = BrowserSession(on_log=self._emit_log)
        self._tasks: dict[str, DownloadTask] = {}
        self._task_counter = 0
        self._history: list[dict[str, Any]] = []
        self._history_lock = threading.Lock()

    def _emit_log(self, msg: str, level: str = "info") -> None:
        if self._on_log:
            self._on_log(msg, level)

    def _emit_progress(self, data: dict[str, Any]) -> None:
        if self._on_progress:
            self._on_progress(data)

    def ensure_browser(self) -> bool:
        if self._session.ready:
            return True
        return self._session.start(headless=True)

    def search(
        self, keyword: str, source: str, search_type: str, number: int
    ) -> list[dict[str, Any]]:
        if not self.ensure_browser():
            return []
        self._emit_log(
            f'搜索 "{keyword}" (来源: {source}, 类型: {search_type}, 数量: {number})...',
            "info",
        )
        results = search_with_pagination(self._session.page, keyword, source, search_type, number)
        seen: set = set()
        unique: list[dict[str, Any]] = []
        for song in results:
            sid = song.get("id", "")
            if sid and sid not in seen:
                seen.add(sid)
                unique.append(normalize_song(song))
        dropped = len(results) - len(unique)
        if dropped:
            self._emit_log(f"跳过 {dropped} 首重复结果", "warn")
        self._emit_log(f"找到 {len(unique)} 首歌曲", "success")
        return unique

    def _run_download(self, task: DownloadTask) -> None:
        os.makedirs(task.output_dir, exist_ok=True)
        safe_dir_name = ""
        if task.songs:
            first_artist = task.songs[0].get("artist", "下载")
            safe_dir_name = sanitize_filename(str(first_artist))
        target_dir = (
            os.path.join(task.output_dir, safe_dir_name) if safe_dir_name else task.output_dir
        )
        os.makedirs(target_dir, exist_ok=True)

        total = len(task.songs)
        self._emit_progress(
            {
                "type": "start",
                "task_id": task.task_id,
                "total": total,
            }
        )

        for idx, song in enumerate(task.songs):
            if task.cancel_event.is_set():
                self._emit_log("下载已取消", "warn")
                break

            name = str(song.get("name", "未知"))
            self._emit_progress(
                {
                    "type": "progress",
                    "task_id": task.task_id,
                    "current": idx,
                    "total": total,
                    "song_name": name,
                }
            )

            result = download_song(
                page=self._session.page,
                context=self._session.context,
                song=song,
                source=task.source,
                save_dir=target_dir,
                index=idx + 1,
                total=total,
                download_lyric=task.download_lyric,
                download_cover=task.download_cover,
                bitrate=task.bitrate,
            )

            if result == "success":
                task.success += 1
                self._emit_log(f"下载完成: {name}", "success")
                artist = str(song.get("artist", "未知"))
                filepath = os.path.join(
                    target_dir,
                    f"[{song.get('id', '')}] {artist} - {name}"
                    + (".flac" if task.bitrate == "flac" else ".mp3"),
                )
                with self._history_lock:
                    self._history.append(
                        {
                            "name": name,
                            "artist": artist,
                            "source": task.source,
                            "bitrate": task.bitrate,
                            "path": filepath,
                            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
            elif result == "skip":
                task.skip += 1
                self._emit_log(f"已存在，跳过: {name}", "warn")
            else:
                task.fail += 1
                self._emit_log(f"下载失败: {name}", "error")

            if idx < total - 1:
                time.sleep(INTER_SONG_DELAY_SEC)

        self._emit_progress(
            {
                "type": "complete",
                "task_id": task.task_id,
                "success": task.success,
                "fail": task.fail,
                "skip": task.skip,
            }
        )
        self._emit_log(
            f"下载完成: 成功 {task.success} / 失败 {task.fail} / 跳过 {task.skip}",
            "success" if task.fail == 0 else "warn",
        )
        self._tasks.pop(task.task_id, None)

    def start_download(
        self,
        songs: list[dict[str, Any]],
        source: str,
        bitrate: str,
        download_lyric: bool,
        download_cover: bool,
        output_dir: str,
    ) -> str:
        if not self.ensure_browser():
            return ""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}_{int(time.time())}"
        task = DownloadTask(
            task_id=task_id,
            songs=songs,
            source=source,
            bitrate=bitrate,
            download_lyric=download_lyric,
            download_cover=download_cover,
            output_dir=output_dir,
        )
        self._tasks[task_id] = task
        thread = threading.Thread(target=self._run_download, args=(task,), daemon=True)
        thread.start()
        return task_id

    def cancel_download(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.cancel_event.set()

    def get_history(self) -> list[dict[str, Any]]:
        with self._history_lock:
            return list(self._history)

    def check_environment(self) -> list[dict[str, Any]]:
        results = run_environment_checks()
        return [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in results]

    def shutdown(self) -> None:
        for task in self._tasks.values():
            task.cancel_event.set()
        time.sleep(0.3)
        self._session.stop()
