"""Bridge layer between GUI and existing core modules.

All Playwright operations run on a dedicated background thread. This avoids
the "cannot switch to a different thread" error that occurs when pywebview
calls Python from different threads while using Playwright's sync API.
"""

from __future__ import annotations

import contextlib
import os
import queue
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from music_downloader.core.config import (
    BASE_URL,
    INTER_SONG_DELAY_SEC,
    PAGE_NAV_TIMEOUT_MS,
    USER_AGENT,
)
from music_downloader.domain.enums import SearchType, Source, source_label
from music_downloader.domain.models import SearchOptions, Song
from music_downloader.infrastructure.downloader import build_output_path, download_song
from music_downloader.infrastructure.environment import run_environment_checks
from music_downloader.infrastructure.files import safe_filename
from music_downloader.infrastructure.gdstudio import GdStudioClient, wait_for_cloudflare
from music_downloader.services.search import SearchService

LogCallback = Callable[[str, str], None]
ProgressCallback = Callable[[dict[str, Any]], None]
CoverCallback = Callable[[dict[str, str]], None]
HEADLESS_WINDOW_POSITION_ARG = "--window-position=-32000,-32000"


def _browser_launch_args(*, headless: bool) -> list[str]:
    return [HEADLESS_WINDOW_POSITION_ARG] if headless else []


@dataclass
class DownloadTask:
    task_id: str
    songs: list[dict[str, Any]]
    source: str
    bitrate: str
    download_lyric: bool
    download_cover: bool
    output_dir: str
    keyword: str = ""
    cancel_event: threading.Event = field(default_factory=threading.Event)
    success: int = 0
    fail: int = 0
    skip: int = 0


class _Task:
    def __init__(self, func: Callable[[], Any], future: threading.Event):
        self.func = func
        self.future = future
        self.result: Any = None
        self.exception: BaseException | None = None


class _PlaywrightThread:
    """Dedicated thread that owns the Playwright browser instance."""

    def __init__(self, on_log: LogCallback | None = None):
        self._on_log = on_log
        self._queue: queue.Queue[_Task] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._ready = threading.Event()
        self._playwright: Any = None
        self._playwright_cm: Any = None
        self._context: Any = None
        self._page: Any = None
        self._browser_ready = threading.Event()

    def _log(self, msg: str, level: str = "info") -> None:
        if self._on_log:
            self._on_log(msg, level)

    def _cleanup_browser(self) -> None:
        """Close and clear browser state on the owning Playwright thread."""
        context = self._context
        self._context = None
        self._page = None
        self._browser_ready.clear()
        if context is not None:
            with contextlib.suppress(Exception):
                context.close()

    def start(self) -> bool:
        if self._thread is not None and self._thread.is_alive():
            return True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5.0)
        return self._thread.is_alive()

    def _run(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self._log("缺少 playwright 依赖，请运行 pip install -r requirements.txt", "error")
            self._ready.set()
            return

        try:
            self._playwright_cm = sync_playwright()
            self._playwright = self._playwright_cm.start()
        except Exception as exc:
            self._log(f"Playwright 启动失败: {exc}", "error")
            self._ready.set()
            return

        self._ready.set()

        while not self._stop_event.is_set():
            try:
                task = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                task.result = task.func()
            except BaseException as exc:
                task.exception = exc
            finally:
                task.future.set()

        # Cleanup on thread exit.
        self._cleanup_browser()
        with contextlib.suppress(Exception):
            if self._playwright is not None:
                self._playwright_cm.stop()
        self._playwright = None

    def submit(self, func: Callable[[], Any], timeout: float | None = None) -> Any:
        """Submit a callable to run on the Playwright thread and block for result."""
        if self._thread is None or not self._thread.is_alive():
            raise RuntimeError("Playwright thread is not running")
        event = threading.Event()
        task = _Task(func, event)
        self._queue.put(task)
        if not event.wait(timeout=timeout):
            raise TimeoutError("Playwright thread task timed out")
        if task.exception is not None:
            raise task.exception
        return task.result

    def start_browser(self, *, headless: bool = True, user_data_dir: str | None = None) -> bool:
        """Start browser on the dedicated thread. Returns True if ready."""
        if self._browser_ready.is_set():
            return True

        if user_data_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            user_data_dir = os.path.join(base_dir, ".chrome-profile")
        os.makedirs(user_data_dir, exist_ok=True)

        final_user_data_dir = user_data_dir
        final_headless = headless
        open_cancelled = threading.Event()

        def _open() -> bool:
            self._cleanup_browser()
            if open_cancelled.is_set():
                return False
            try:
                self._log("正在启动浏览器...", "info")
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=final_user_data_dir,
                    channel="chrome",
                    headless=final_headless,
                    user_agent=USER_AGENT,
                    args=_browser_launch_args(headless=final_headless),
                )
                self._page = (
                    self._context.pages[0] if self._context.pages else self._context.new_page()
                )
                self._log("正在访问音乐站点，等待 Cloudflare 验证...", "info")
                self._page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
                cf_passed = wait_for_cloudflare(self._page)

                if not cf_passed and final_headless:
                    self._log("无头模式未通过验证，尝试有头模式...", "warn")
                    self._cleanup_browser()
                    self._context = self._playwright.chromium.launch_persistent_context(
                        user_data_dir=final_user_data_dir,
                        channel="chrome",
                        headless=False,
                        user_agent=USER_AGENT,
                        args=_browser_launch_args(headless=False),
                    )
                    self._page = (
                        self._context.pages[0] if self._context.pages else self._context.new_page()
                    )
                    self._page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
                    cf_passed = wait_for_cloudflare(self._page)

                if cf_passed and not open_cancelled.is_set():
                    self._log("浏览器就绪，Cloudflare 验证通过", "success")
                    self._browser_ready.set()
                    return True
                self._log("Cloudflare 验证未通过", "error")
                return False
            finally:
                if not self._browser_ready.is_set():
                    self._cleanup_browser()

        try:
            return self.submit(_open, timeout=120.0)
        except TimeoutError as exc:
            open_cancelled.set()
            self._log(f"浏览器启动失败: {exc}", "error")
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
        self._stop_event.set()
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=5.0)


class MusicBridge:
    """High-level bridge that GUI api.py calls into."""

    def __init__(
        self,
        on_log: LogCallback | None = None,
        on_progress: ProgressCallback | None = None,
        on_cover: CoverCallback | None = None,
    ):
        self._on_log = on_log
        self._on_progress = on_progress
        self._on_cover = on_cover
        self._session = _PlaywrightThread(on_log=self._emit_log)
        self._tasks: dict[str, DownloadTask] = {}
        self._task_counter = 0
        self._cover_generation = 0

    def _emit_log(self, msg: str, level: str = "info") -> None:
        if self._on_log:
            self._on_log(msg, level)

    def _emit_progress(self, data: dict[str, Any]) -> None:
        if self._on_progress:
            self._on_progress(data)

    def _emit_cover(self, data: dict[str, str]) -> None:
        if self._on_cover:
            self._on_cover(data)

    def _resolve_covers(self, songs: list[Song], source: str, generation: int) -> None:
        client = GdStudioClient(self._session.page)
        for song in songs:
            if generation != self._cover_generation:
                return
            if not song.pic_id:
                continue
            try:

                def _get_cover(current: Song = song) -> str:
                    return client.get_pic_url(current, source)

                cover = self._session.submit(
                    _get_cover,
                    timeout=60.0,
                )
            except Exception:  # noqa: BLE001
                if generation != self._cover_generation:
                    return
                continue
            if generation != self._cover_generation:
                return
            if cover:
                self._emit_cover({"id": song.id, "source": source, "cover": str(cover)})

    def _start_cover_resolution(
        self,
        songs: list[Song],
        source: str,
        generation: int,
    ) -> None:
        if not songs or self._on_cover is None:
            return
        thread = threading.Thread(
            target=self._resolve_covers,
            args=(songs, source, generation),
            daemon=True,
        )
        thread.start()

    def ensure_browser(self) -> bool:
        if self._session.ready:
            return True
        if not self._session.start():
            return False
        return self._session.start_browser(headless=True)

    def search(
        self, keyword: str, source: str, search_type: str, number: int
    ) -> list[dict[str, Any]]:
        self._cover_generation += 1
        cover_generation = self._cover_generation
        if not self.ensure_browser():
            return []
        self._emit_log(
            f'搜索 "{keyword}" (来源: {source_label(source)} ({source}), '
            f"类型: {search_type}, 数量: {number})...",
            "info",
        )

        def _do_search() -> list[Song]:
            client = GdStudioClient(self._session.page)
            return SearchService(client).search(
                SearchOptions(
                    keyword=keyword,
                    source=Source(source),
                    search_type=SearchType(search_type),
                    number=number,
                )
            )

        songs = self._session.submit(_do_search, timeout=120.0)
        results = [song.to_result_dict() for song in songs]
        self._emit_log(f"找到 {len(results)} 首歌曲", "success")
        self._start_cover_resolution(songs, source, cover_generation)
        return results

    def _fail_unfinished_downloads(
        self,
        task: DownloadTask,
        start_index: int,
        target_dir: str,
        reason: str,
    ) -> None:
        total = len(task.songs)
        for idx in range(start_index, total):
            song = task.songs[idx]
            try:
                song_index = int(song.get("_gui_index", idx))
            except (TypeError, ValueError):
                song_index = idx
            task.fail += 1
            self._emit_progress(
                {
                    "type": "song_done",
                    "task_id": task.task_id,
                    "index": song_index,
                    "result": "fail",
                    "reason": reason,
                    "path": build_output_path(target_dir, song, task.bitrate),
                    "current": idx + 1,
                    "total": total,
                }
            )

    def _run_download(self, task: DownloadTask) -> None:
        output_dir = task.output_dir
        target_dir = output_dir
        next_index = 0
        try:
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as exc:
                self._emit_log(
                    f"无法创建下载目录 {output_dir} ({exc})，尝试使用项目 downloads/ 目录",
                    "warn",
                )
                output_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                    "downloads",
                )
                os.makedirs(output_dir, exist_ok=True)

            safe_dir_name = safe_filename(task.keyword.strip()) if task.keyword.strip() else ""
            if not safe_dir_name and task.songs:
                first_artist = task.songs[0].get("artist", "下载")
                safe_dir_name = safe_filename(str(first_artist))
            target_dir = os.path.join(output_dir, safe_dir_name) if safe_dir_name else output_dir
            try:
                os.makedirs(target_dir, exist_ok=True)
            except OSError as exc:
                self._emit_log(f"无法创建目标目录 {target_dir}: {exc}", "error")
                self._fail_unfinished_downloads(
                    task,
                    0,
                    target_dir,
                    "无法创建下载目录",
                )
                return

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

                def _do_download(
                    _song: dict[str, Any] = song,
                    _idx: int = idx,
                    _total: int = total,
                ) -> str:
                    return download_song(
                        page=self._session.page,
                        context=self._session.context,
                        song=_song,
                        source=task.source,
                        save_dir=target_dir,
                        index=_idx + 1,
                        total=_total,
                        download_lyric=task.download_lyric,
                        download_cover=task.download_cover,
                        bitrate=task.bitrate,
                    )

                result = self._session.submit(_do_download, timeout=300.0)

                # 原始索引用于前端状态更新
                try:
                    song_index = int(song.get("_gui_index", idx))
                except (TypeError, ValueError):
                    song_index = idx

                filepath = build_output_path(target_dir, song, task.bitrate)
                reason = ""

                if result == "success":
                    task.success += 1
                    self._emit_log(f"下载完成: {name}", "success")
                    self._emit_progress(
                        {
                            "type": "song_done",
                            "task_id": task.task_id,
                            "index": song_index,
                            "result": "success",
                            "reason": reason,
                            "path": filepath,
                            "current": idx + 1,
                            "total": total,
                        }
                    )
                elif result == "skip":
                    task.skip += 1
                    self._emit_log(f"已存在，跳过: {name}", "warn")
                    self._emit_progress(
                        {
                            "type": "song_done",
                            "task_id": task.task_id,
                            "index": song_index,
                            "result": "skip",
                            "reason": reason,
                            "path": filepath,
                            "current": idx + 1,
                            "total": total,
                        }
                    )
                else:
                    task.fail += 1
                    reason = "下载失败，请查看日志"
                    self._emit_log(f"下载失败: {name}", "error")
                    self._emit_progress(
                        {
                            "type": "song_done",
                            "task_id": task.task_id,
                            "index": song_index,
                            "result": "fail",
                            "reason": reason,
                            "path": filepath,
                            "current": idx + 1,
                            "total": total,
                        }
                    )

                next_index = idx + 1
                if idx < total - 1:
                    time.sleep(INTER_SONG_DELAY_SEC)

        except Exception as exc:  # noqa: BLE001 - worker must always publish a terminal event
            self._emit_log(f"下载任务异常: {exc}", "error")
            if not task.cancel_event.is_set():
                self._fail_unfinished_downloads(
                    task,
                    next_index,
                    target_dir,
                    "下载任务异常，请查看日志",
                )
        finally:
            try:
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
            finally:
                self._tasks.pop(task.task_id, None)

    def start_download(
        self,
        songs: list[dict[str, Any]],
        source: str,
        bitrate: str,
        download_lyric: bool,
        download_cover: bool,
        output_dir: str,
        keyword: str = "",
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
            keyword=keyword,
        )
        self._tasks[task_id] = task
        thread = threading.Thread(target=self._run_download, args=(task,), daemon=True)
        thread.start()
        return task_id

    def cancel_download(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task.cancel_event.set()

    def check_environment(self) -> list[dict[str, Any]]:
        results = run_environment_checks()
        return [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in results]

    def shutdown(self) -> None:
        self._cover_generation += 1
        for task in self._tasks.values():
            task.cancel_event.set()
        time.sleep(0.3)
        self._session.stop()
