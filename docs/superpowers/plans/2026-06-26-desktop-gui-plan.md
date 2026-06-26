# Desktop GUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a desktop GUI (powered by pywebview) to the existing music downloader CLI tool, with the GUI as the default mode when no CLI arguments are provided, while fully preserving existing CLI functionality.

**Architecture:** pywebview creates a native desktop window (WebView2 on Windows) loading local HTML/CSS/JS. Python backend exposes a `MusicApi` class via pywebview's JS bridge. The bridge layer wraps existing core modules (`api.py`, `downloader.py`, etc.) without modifying them, running long operations in background threads to avoid blocking the UI. Event callbacks push log messages and download progress to the frontend.

**Tech Stack:** Python 3.10+, pywebview 5.x, vanilla TypeScript/JavaScript (no framework), HTML5/CSS3, Nuitka for packaging.

**Spec Reference:** [2026-06-26-desktop-gui-design.md](file:///f:/traeIde/docs/superpowers/specs/2026-06-26-desktop-gui-design.md)

---

## File Structure

New files to create:
```
music_downloader/gui/
├── __init__.py            # Package marker
├── app.py                 # GUI entry point: creates pywebview window, starts event loop
├── api.py                 # MusicApi class exposed to frontend JS via pywebview
├── bridge.py              # Bridge layer: wraps existing core logic, thread management, event dispatch
├── settings.py            # User settings persistence (JSON config file in user home)
└── static/
    ├── index.html         # Main window HTML
    ├── css/
    │   └── style.css      # UI styles (light theme, indigo #4f46e5 primary, left-right layout)
    └── js/
        └── app.js         # Frontend logic: API calls, DOM rendering, event handling
```

Files to modify:
- `requirements.txt` — add pywebview dependency
- `music_downloader/cli.py` — add `--gui` argument, add GUI launch logic when no args
- `scripts/build_exe.ps1` — include GUI static resources in Nuitka build

Existing core files (api.py, downloader.py, metadata.py, display.py, etc.) are **not modified**.

---

## Task 1: Add Dependency and Create GUI Module Skeleton

**Files:**
- Modify: `requirements.txt`
- Create: `music_downloader/gui/__init__.py`

- [ ] **Step 1: Add pywebview to requirements.txt**

Read the current `requirements.txt` and append pywebview. The file should look like:

```text
# -*-coding:utf-8 -*-
playwright>=1.45
mutagen>=1.47
rich>=13
rich-argparse>=1.8
pywebview>=5.0
```

- [ ] **Step 2: Create gui package directory and __init__.py**

Run:
```powershell
New-Item -ItemType Directory -Force -Path "f:\traeIde\music_downloader\gui\static\css","f:\traeIde\music_downloader\gui\static\js" | Out-Null
```

Create `music_downloader/gui/__init__.py`:
```python
"""Desktop GUI module for music downloader."""
```

- [ ] **Step 3: Verify syntax and imports**

Run:
```powershell
python -m py_compile music_downloader/gui/__init__.py
Write-Host "OK"
```
Expected: Prints "OK" with no errors.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt music_downloader/gui/__init__.py
git commit -m "feat(gui): add pywebview dependency and gui package skeleton"
```

---

## Task 2: Implement Settings Persistence

**Files:**
- Create: `music_downloader/gui/settings.py`

- [ ] **Step 1: Create settings.py with config load/save**

Create `music_downloader/gui/settings.py`:

```python
"""User settings persistence for the GUI.

Settings are stored as JSON in the user's home directory:
~/.music_downloader_config.json
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_FILENAME = ".music_downloader_config.json"


def _get_config_path() -> Path:
    return Path.home() / CONFIG_FILENAME


DEFAULT_CONFIG: dict[str, Any] = {
    "source": "netease",
    "search_type": "song",
    "bitrate": "320",
    "number": 20,
    "output_dir": "",
    "download_cover": True,
    "download_lyric": True,
    "window_width": 960,
    "window_height": 680,
}


def load_config() -> dict[str, Any]:
    """Load config from disk, merging with defaults for missing keys."""
    path = _get_config_path()
    config = dict(DEFAULT_CONFIG)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                config.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    if not config.get("output_dir"):
        config["output_dir"] = str(Path.home() / "Downloads" / "MusicDownloader")
    return config


def save_config(config: dict[str, Any]) -> None:
    """Save config to disk, preserving only known keys."""
    path = _get_config_path()
    to_save = {k: config.get(k, DEFAULT_CONFIG[k]) for k in DEFAULT_CONFIG}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
```

- [ ] **Step 2: Verify syntax**

Run:
```powershell
python -m py_compile music_downloader/gui/settings.py
Write-Host "OK"
```
Expected: Prints "OK" with no errors.

- [ ] **Step 3: Quick smoke test (load/save round-trip)**

Run:
```powershell
python -c "from music_downloader.gui.settings import load_config, save_config; c = load_config(); print('Default source:', c['source']); c['source'] = 'spotify'; save_config(c); c2 = load_config(); print('After save:', c2['source']); c['source'] = 'netease'; save_config(c); print('Reset OK')"
```
Expected: Prints "Default source: netease", "After save: spotify", "Reset OK".

- [ ] **Step 4: Commit**

```bash
git add music_downloader/gui/settings.py
git commit -m "feat(gui): add user settings persistence (JSON config)"
```

---

## Task 3: Implement Bridge Layer

**Files:**
- Create: `music_downloader/gui/bridge.py`

- [ ] **Step 1: Create bridge.py with browser/session management and download threading**

Create `music_downloader/gui/bridge.py`:

```python
"""Bridge layer between GUI and existing core modules.

Wraps Playwright browser lifecycle, search, and download operations
in a thread-safe manner suitable for GUI use. Long operations run on
background threads and emit events via callbacks.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from music_downloader.api import (
    get_lyric,
    get_pic_url,
    get_play_url,
    search_with_pagination,
    wait_for_cloudflare,
)
from music_downloader.config import (
    BASE_URL,
    COVER_TIMEOUT_MS,
    DOWNLOAD_RETRIES,
    INTER_SONG_DELAY_SEC,
    MIN_DOWNLOAD_BYTES,
    PAGE_NAV_TIMEOUT_MS,
    PROXY_BASE_URL,
    REQUEST_TIMEOUT_MS,
    USER_AGENT,
)
from music_downloader.metadata import embed_metadata
from music_downloader.utils import get_artist_str, sanitize_filename

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
                user_data_dir = os.path.abspath(
                    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".chrome-profile")
                )
            os.makedirs(user_data_dir, exist_ok=True)

            try:
                self._playwright_cm = sync_playwright()
                self._playwright = self._playwright_cm.start()
                self._log("正在启动浏览器...", "info")
                self._context = self._playwright.chromium.launch_persistent_context(
                    user_data_dir=user_data_dir,
                    channel="chrome",
                    headless=headless,
                    user_agent=USER_AGENT,
                )
                self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
                self._log("正在访问音乐站点，等待 Cloudflare 验证...", "info")
                self._page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
                self._cf_passed = wait_for_cloudflare(self._page)
                if not self._cf_passed and headless:
                    self._log("无头模式未通过验证，尝试有头模式...", "warn")
                    self._context.close()
                    self._context = self._playwright.chromium.launch_persistent_context(
                        user_data_dir=user_data_dir,
                        channel="chrome",
                        headless=False,
                        user_agent=USER_AGENT,
                    )
                    self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
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
    def page(self):
        return self._page

    @property
    def context(self):
        return self._context

    @property
    def ready(self) -> bool:
        return self._browser_ready.is_set()

    def stop(self) -> None:
        with self._lock:
            if self._context is not None:
                try:
                    self._context.close()
                except Exception:
                    pass
                self._context = None
            if self._playwright is not None:
                try:
                    self._playwright_cm.stop()
                except Exception:
                    pass
                self._playwright = None
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

    def search(self, keyword: str, source: str, search_type: str, number: int) -> list[dict[str, Any]]:
        if not self.ensure_browser():
            return []
        from music_downloader.utils import normalize_song
        self._emit_log(f'搜索 "{keyword}" (来源: {source}, 类型: {search_type}, 数量: {number})...', "info")
        results = search_with_pagination(
            self._session.page, keyword, source, search_type, number
        )
        seen: set = set()
        unique = []
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

    def _download_one(self, task: DownloadTask, song: dict, index: int) -> str:
        name = str(song.get("name", "未知"))
        artist = get_artist_str(song)
        bitrate = task.bitrate
        from music_downloader.downloader import build_output_path, _download_body_to_file

        filepath = build_output_path(task.output_dir, song, bitrate)
        filename = os.path.basename(filepath)
        tmp_path = filepath + ".tmp"

        if os.path.exists(filepath):
            self._emit_log(f"已存在，跳过: {filename}", "warn")
            return "skip"

        for attempt in range(1, DOWNLOAD_RETRIES + 1):
            if task.cancel_event.is_set():
                return "fail"
            play_url = get_play_url(self._session.page, song, task.source, bitrate)
            if not play_url:
                if attempt >= DOWNLOAD_RETRIES:
                    self._emit_log(f"未获取到播放链接: {name}", "error")
                    return "fail"
                time.sleep(1.0)
                continue
            proxy_url = f"{PROXY_BASE_URL}/{play_url}"
            if _download_body_to_file(self._session.context, proxy_url, tmp_path, filepath):
                cover_data = b""
                cover_mime = "image/jpeg"
                lyric_text = ""
                if task.download_lyric:
                    lyric_text = get_lyric(self._session.page, song, task.source)
                if task.download_cover:
                    pic_url = get_pic_url(self._session.page, song, task.source)
                    if pic_url:
                        try:
                            resp = self._session.context.request.get(pic_url, timeout=COVER_TIMEOUT_MS)
                            if resp.ok:
                                cover_data = resp.body()
                                cover_mime = resp.headers.get("content-type", "image/jpeg")
                        except Exception:
                            pass
                try:
                    embed_metadata(
                        filepath=filepath, song=song, index=index, total=len(task.songs),
                        cover_data=cover_data, cover_mime=cover_mime,
                        lyric_text=lyric_text, bitrate=bitrate,
                    )
                    self._emit_log(f"下载完成: {filename}", "success")
                    self._history.append({
                        "name": name, "artist": artist, "source": task.source,
                        "bitrate": bitrate, "path": filepath,
                        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    return "success"
                except Exception as exc:
                    self._emit_log(f"写入元数据失败: {exc}", "error")
                    try:
                        os.remove(filepath)
                    except OSError:
                        pass
                    return "fail"
            if attempt >= DOWNLOAD_RETRIES:
                return "fail"
            time.sleep(1.0)
        return "fail"

    def _run_download(self, task: DownloadTask) -> None:
        os.makedirs(task.output_dir, exist_ok=True)
        total = len(task.songs)
        self._emit_progress({
            "type": "start", "task_id": task.task_id, "total": total,
        })
        for idx, song in enumerate(task.songs):
            if task.cancel_event.is_set():
                self._emit_log("下载已取消", "warn")
                break
            name = str(song.get("name", "未知"))
            self._emit_progress({
                "type": "progress", "task_id": task.task_id,
                "current": idx, "total": total, "song_name": name,
            })
            result = self._download_one(task, song, idx + 1)
            if result == "success":
                task.success += 1
            elif result == "skip":
                task.skip += 1
            else:
                task.fail += 1
            if idx < total - 1:
                time.sleep(INTER_SONG_DELAY_SEC)
        self._emit_progress({
            "type": "complete", "task_id": task.task_id,
            "success": task.success, "fail": task.fail, "skip": task.skip,
        })
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
        safe_dir = os.path.join(output_dir, sanitize_filename(songs[0].get("artist", "未知") if songs else "download"))
        task = DownloadTask(
            task_id=task_id, songs=songs, source=source, bitrate=bitrate,
            download_lyric=download_lyric, download_cover=download_cover,
            output_dir=output_dir if not songs else safe_dir,
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
        return list(self._history)

    def check_environment(self) -> list[dict[str, Any]]:
        from music_downloader.env import run_environment_checks
        results = run_environment_checks()
        return [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in results]

    def shutdown(self) -> None:
        for task in self._tasks.values():
            task.cancel_event.set()
        self._session.stop()
```

- [ ] **Step 2: Verify syntax**

Run:
```powershell
python -m py_compile music_downloader/gui/bridge.py
Write-Host "OK"
```
Expected: Prints "OK" with no errors.

- [ ] **Step 3: Commit**

```bash
git add music_downloader/gui/bridge.py
git commit -m "feat(gui): add bridge layer with browser session, search, and threaded download"
```

---

## Task 4: Implement MusicApi Class (Exposed to Frontend)

**Files:**
- Create: `music_downloader/gui/api.py`

- [ ] **Step 1: Create api.py with MusicApi class**

Create `music_downloader/gui/api.py`:

```python
"""Python API exposed to the frontend JS via pywebview bridge."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from music_downloader.config import VALID_BITRATES, VALID_SOURCES, VALID_FORMATS, SEARCH_TYPE_MAP
from music_downloader.gui.bridge import MusicBridge
from music_downloader.gui.settings import load_config, save_config


class MusicApi:
    """API class exposed to JavaScript as window.pywebview.api.

    All public methods are callable from the frontend. Methods that start
    long-running operations (browser init, search, download) are exposed
    as pywebview threadsafe functions so they don't block the UI thread.
    """

    def __init__(self) -> None:
        self._window = None
        self._bridge = MusicBridge(
            on_log=self._handle_log,
            on_progress=self._handle_progress,
        )
        self._listeners: dict[str, list[Any]] = {
            "log": [],
            "progress": [],
        }

    def set_window(self, window: Any) -> None:
        self._window = window

    def _handle_log(self, msg: str, level: str) -> None:
        self._emit("log", {"message": msg, "level": level})

    def _handle_progress(self, data: dict[str, Any]) -> None:
        self._emit("progress", data)

    def _emit(self, event: str, data: dict[str, Any]) -> None:
        if self._window is not None:
            try:
                self._window.evaluate_js(f"window.dispatchEvent(new CustomEvent('py-{event}', {{detail: {__import__('json').dumps(data, ensure_ascii=False)}}}));")
            except Exception:
                pass

    def get_config(self) -> dict[str, Any]:
        return load_config()

    def save_config(self, config: dict[str, Any]) -> bool:
        try:
            save_config(config)
            return True
        except Exception:
            return False

    def get_valid_options(self) -> dict[str, Any]:
        return {
            "sources": [{"value": s, "label": _SOURCE_LABELS.get(s, s)} for s in VALID_SOURCES],
            "bitrates": VALID_BITRATES,
            "search_types": list(SEARCH_TYPE_MAP.keys()),
            "formats": VALID_FORMATS,
        }

    def init_browser(self) -> dict[str, Any]:
        ok = self._bridge.ensure_browser()
        return {"ready": ok}

    def search(self, keyword: str, source: str, search_type: str, number: int) -> list[dict[str, Any]]:
        try:
            num = int(number)
            if num < 1:
                num = 20
        except (TypeError, ValueError):
            num = 20
        return self._bridge.search(keyword, source, search_type, num)

    def start_download(
        self,
        songs: list[dict[str, Any]],
        source: str,
        bitrate: str,
        download_lyric: bool,
        download_cover: bool,
        output_dir: str,
    ) -> str:
        if not output_dir:
            config = load_config()
            output_dir = config.get("output_dir", str(Path.home() / "Downloads" / "MusicDownloader"))
        os.makedirs(output_dir, exist_ok=True)
        return self._bridge.start_download(
            songs=songs, source=source, bitrate=bitrate,
            download_lyric=download_lyric, download_cover=download_cover,
            output_dir=output_dir,
        )

    def cancel_download(self, task_id: str) -> None:
        self._bridge.cancel_download(task_id)

    def open_download_dir(self, path: str = "") -> None:
        target = path or load_config().get("output_dir", str(Path.home() / "Downloads"))
        if not os.path.exists(target):
            os.makedirs(target, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(target)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception:
            pass

    def select_directory(self) -> str:
        from tkinter import Tk, filedialog
        root = Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title="选择下载目录")
        root.destroy()
        return path

    def check_environment(self) -> list[dict[str, Any]]:
        return self._bridge.check_environment()

    def get_history(self) -> list[dict[str, Any]]:
        return self._bridge.get_history()

    def shutdown(self) -> None:
        self._bridge.shutdown()


_SOURCE_LABELS: dict[str, str] = {
    "netease": "网易云音乐",
    "migu": "咪咕音乐",
    "kuwo": "酷我音乐",
    "ytmusic": "YouTube Music",
    "tidal": "Tidal",
    "qobuz": "Qobuz",
    "deezer": "Deezer",
    "spotify": "Spotify",
    "tencent": "QQ音乐",
    "ximalaya": "喜马拉雅",
    "joox": "Joox",
    "apple": "Apple Music",
}
```

- [ ] **Step 2: Verify syntax**

Run:
```powershell
python -m py_compile music_downloader/gui/api.py
Write-Host "OK"
```
Expected: Prints "OK" with no errors.

- [ ] **Step 3: Quick import test**

Run:
```powershell
python -c "from music_downloader.gui.api import MusicApi; api = MusicApi(); print('MusicApi created OK'); opts = api.get_valid_options(); print('Sources:', len(opts['sources']))"
```
Expected: Prints "MusicApi created OK", "Sources: 12".

- [ ] **Step 4: Commit**

```bash
git add music_downloader/gui/api.py
git commit -m "feat(gui): add MusicApi class exposed to frontend via pywebview"
```

---

## Task 5: Create Frontend HTML Skeleton

**Files:**
- Create: `music_downloader/gui/static/index.html`

- [ ] **Step 1: Create index.html**

Create `music_downloader/gui/static/index.html`:

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>音乐下载器</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <div id="app" class="app-container">
    <!-- Left Sidebar -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="app-title">🎵 音乐下载器</h1>
      </div>

      <div class="sidebar-section">
        <div class="search-box">
          <input type="text" id="searchInput" class="input-field" placeholder="搜索歌曲、歌手、专辑..." />
          <button id="searchBtn" class="btn btn-primary btn-full">搜索</button>
        </div>
      </div>

      <div class="sidebar-section">
        <label class="field-label">音乐源</label>
        <select id="sourceSelect" class="input-field"></select>

        <label class="field-label">搜索类型</label>
        <select id="typeSelect" class="input-field">
          <option value="song">单曲</option>
          <option value="album">专辑</option>
          <option value="playlist">歌单</option>
        </select>

        <label class="field-label">音质</label>
        <select id="bitrateSelect" class="input-field">
          <option value="128">128kbps</option>
          <option value="192">192kbps</option>
          <option value="320">320kbps</option>
          <option value="flac">FLAC</option>
        </select>

        <label class="field-label">数量</label>
        <input type="number" id="numberInput" class="input-field" value="20" min="1" max="999" />

        <div class="checkbox-row">
          <label class="checkbox-label"><input type="checkbox" id="coverCheck" checked /> 下载封面</label>
          <label class="checkbox-label"><input type="checkbox" id="lyricCheck" checked /> 下载歌词</label>
        </div>
      </div>

      <div class="sidebar-section">
        <label class="field-label">下载目录</label>
        <div class="dir-row">
          <input type="text" id="outputDirInput" class="input-field input-sm" readonly />
          <button id="browseDirBtn" class="btn btn-sm">浏览</button>
        </div>
        <button id="openDirBtn" class="btn btn-outline btn-full">📁 打开下载目录</button>
      </div>

      <div class="sidebar-footer">
        <button id="envCheckBtn" class="btn btn-ghost btn-full">🔍 环境检查</button>
      </div>
    </aside>

    <!-- Main Content -->
    <main class="main-content">
      <div class="toolbar">
        <button id="downloadSelectedBtn" class="btn btn-primary">⬇ 下载选中</button>
        <button id="selectAllBtn" class="btn btn-outline">全选</button>
        <button id="deselectAllBtn" class="btn btn-outline">取消全选</button>
        <div class="toolbar-spacer"></div>
        <span id="resultCount" class="result-count"></span>
      </div>

      <div id="resultList" class="result-list">
        <div class="empty-state">
          <div class="empty-icon">🎵</div>
          <p>输入关键词开始搜索</p>
        </div>
      </div>

      <div class="download-panel" id="downloadPanel" style="display:none;">
        <div class="progress-row">
          <span id="progressLabel" class="progress-label">准备下载...</span>
          <div class="progress-bar-container">
            <div id="progressBar" class="progress-bar" style="width:0%"></div>
          </div>
          <span id="progressText" class="progress-text">0/0</span>
          <button id="cancelDownloadBtn" class="btn btn-sm btn-danger">取消</button>
        </div>
      </div>

      <div class="log-panel">
        <div class="log-header">
          <span>📋 日志</span>
          <button id="toggleLogBtn" class="btn btn-ghost btn-xs">折叠</button>
        </div>
        <div id="logContent" class="log-content"></div>
      </div>
    </main>
  </div>

  <!-- Environment Check Modal -->
  <div id="envModal" class="modal-overlay" style="display:none;">
    <div class="modal">
      <div class="modal-header">
        <h3>环境检查</h3>
        <button id="closeEnvModal" class="btn-close">&times;</button>
      </div>
      <div id="envModalBody" class="modal-body"></div>
    </div>
  </div>

  <!-- Loading Overlay -->
  <div id="loadingOverlay" class="loading-overlay" style="display:none;">
    <div class="spinner"></div>
    <p id="loadingText">加载中...</p>
  </div>

  <script src="js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify the file exists and is valid**

Run:
```powershell
Test-Path "f:\traeIde\music_downloader\gui\static\index.html"
```
Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add music_downloader/gui/static/index.html
git commit -m "feat(gui): add frontend HTML skeleton with left-right layout"
```

---

## Task 6: Implement CSS Styles (Light Theme, Indigo Primary)

**Files:**
- Create: `music_downloader/gui/static/css/style.css`

- [ ] **Step 1: Create style.css**

Create `music_downloader/gui/static/css/style.css`:

```css
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --primary-light: #eef2ff;
  --danger: #ef4444;
  --success: #10b981;
  --warn: #f59e0b;
  --bg: #ffffff;
  --bg-sidebar: #f9fafb;
  --bg-hover: #f3f4f6;
  --bg-active: #eef2ff;
  --border: #e5e7eb;
  --text: #111827;
  --text-secondary: #6b7280;
  --text-muted: #9ca3af;
  --radius: 6px;
  --radius-sm: 4px;
  --shadow: 0 1px 3px rgba(0,0,0,0.08);
}

html, body {
  height: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 13px;
  color: var(--text);
  background: var(--bg);
  overflow: hidden;
  user-select: none;
}

.app-container {
  display: flex;
  height: 100vh;
}

/* Sidebar */
.sidebar {
  width: 220px;
  min-width: 220px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  padding: 12px;
  overflow-y: auto;
}

.sidebar-header {
  margin-bottom: 12px;
}

.app-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--primary);
}

.sidebar-section {
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.sidebar-section:last-of-type {
  border-bottom: none;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 10px;
}

.field-label {
  display: block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 8px 0 4px;
}

.input-field {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 12px;
  background: white;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
}

.input-field:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(79,70,229,0.15);
}

.input-sm {
  flex: 1;
}

.checkbox-row {
  display: flex;
  gap: 10px;
  margin-top: 8px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.dir-row {
  display: flex;
  gap: 4px;
  align-items: center;
}

/* Buttons */
.btn {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: white;
  color: var(--text);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.btn:hover {
  background: var(--bg-hover);
}

.btn-primary {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.btn-primary:hover {
  background: var(--primary-hover);
}

.btn-outline {
  background: white;
  color: var(--primary);
  border-color: var(--border);
}

.btn-outline:hover {
  background: var(--primary-light);
  border-color: var(--primary);
}

.btn-ghost {
  background: transparent;
  border-color: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.btn-danger {
  background: var(--danger);
  color: white;
  border-color: var(--danger);
}

.btn-danger:hover {
  background: #dc2626;
}

.btn-sm {
  padding: 4px 8px;
  font-size: 11px;
}

.btn-xs {
  padding: 2px 6px;
  font-size: 10px;
}

.btn-full {
  width: 100%;
  margin-top: 6px;
}

.search-box {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  background: white;
}

.toolbar-spacer {
  flex: 1;
}

.result-count {
  font-size: 12px;
  color: var(--text-muted);
}

.result-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 0;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.song-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 14px;
  border-bottom: 1px solid #f3f4f6;
  cursor: pointer;
  transition: background 0.1s;
}

.song-item:hover {
  background: var(--bg-hover);
}

.song-item.selected {
  background: var(--primary-light);
}

.song-item.downloaded {
  opacity: 0.6;
}

.song-check {
  width: 16px;
  height: 16px;
  cursor: pointer;
  flex-shrink: 0;
}

.song-cover {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 16px;
  flex-shrink: 0;
}

.song-info {
  flex: 1;
  min-width: 0;
}

.song-name {
  font-weight: 600;
  font-size: 13px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.song-meta {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.song-duration {
  font-size: 11px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.song-status {
  font-size: 14px;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

.status-done { color: var(--success); }
.status-fail { color: var(--danger); }
.status-downloading { color: var(--primary); }

.source-tag {
  display: inline-block;
  padding: 1px 5px;
  background: var(--bg-hover);
  border-radius: 3px;
  font-size: 10px;
  color: var(--text-muted);
  margin-left: 6px;
}

.hires-tag {
  display: inline-block;
  padding: 1px 4px;
  background: #fef3c7;
  color: #92400e;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 600;
  margin-left: 4px;
}

/* Download Panel */
.download-panel {
  padding: 8px 14px;
  border-top: 1px solid var(--border);
  background: var(--bg-sidebar);
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-label {
  font-size: 11px;
  color: var(--text-secondary);
  white-space: nowrap;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress-bar-container {
  flex: 1;
  height: 6px;
  background: var(--border);
  border-radius: 3px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: var(--primary);
  border-radius: 3px;
  transition: width 0.3s;
}

.progress-text {
  font-size: 11px;
  color: var(--text-muted);
  min-width: 40px;
  text-align: right;
}

/* Log Panel */
.log-panel {
  border-top: 1px solid var(--border);
  background: #fafafa;
  max-height: 120px;
  transition: max-height 0.2s;
  overflow: hidden;
}

.log-panel.collapsed {
  max-height: 28px;
}

.log-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
}

.log-content {
  height: calc(100% - 26px);
  overflow-y: auto;
  padding: 4px 10px;
  font-family: "Cascadia Code", "Consolas", "Microsoft YaHei", monospace;
  font-size: 11px;
  line-height: 1.6;
}

.log-entry {
  white-space: nowrap;
}

.log-info { color: var(--text-secondary); }
.log-success { color: var(--success); }
.log-warn { color: var(--warn); }
.log-error { color: var(--danger); }

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 8px;
  width: 420px;
  max-width: 90vw;
  box-shadow: 0 10px 40px rgba(0,0,0,0.15);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.modal-header h3 {
  font-size: 14px;
}

.btn-close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: var(--text-muted);
  padding: 0 4px;
}

.btn-close:hover {
  color: var(--text);
}

.modal-body {
  padding: 16px;
}

.env-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f3f4f6;
}

.env-item:last-child { border-bottom: none; }

.env-status-ok { color: var(--success); font-weight: 600; }
.env-status-fail { color: var(--danger); font-weight: 600; }
.env-detail { font-size: 11px; color: var(--text-muted); }

/* Loading */
.loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255,255,255,0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

#loadingText {
  font-size: 13px;
  color: var(--text-secondary);
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
```

- [ ] **Step 2: Verify file exists**

Run:
```powershell
Test-Path "f:\traeIde\music_downloader\gui\static\css\style.css"
```
Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add music_downloader/gui/static/css/style.css
git commit -m "feat(gui): add CSS styles - light theme, indigo primary, left-right layout"
```

---

## Task 7: Implement Frontend JavaScript Logic

**Files:**
- Create: `music_downloader/gui/static/js/app.js`

- [ ] **Step 1: Create app.js**

Create `music_downloader/gui/static/js/app.js`:

```javascript
(function() {
  'use strict';

  const state = {
    config: null,
    songs: [],
    selectedIndices: new Set(),
    currentTaskId: null,
    logCollapsed: false,
  };

  const $ = (id) => document.getElementById(id);

  function log(msg, level) {
    level = level || 'info';
    const el = $('logContent');
    const entry = document.createElement('div');
    entry.className = 'log-entry log-' + level;
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    entry.textContent = '[' + time + '] ' + msg;
    el.appendChild(entry);
    el.scrollTop = el.scrollHeight;
  }

  function showLoading(text) {
    $('loadingText').textContent = text || '加载中...';
    $('loadingOverlay').style.display = 'flex';
  }

  function hideLoading() {
    $('loadingOverlay').style.display = 'none';
  }

  function setProgress(current, total, songName) {
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    $('progressBar').style.width = pct + '%';
    $('progressText').textContent = current + '/' + total;
    if (songName) {
      $('progressLabel').textContent = '下载中: ' + songName;
    }
  }

  function showDownloadPanel() {
    $('downloadPanel').style.display = 'block';
  }

  function hideDownloadPanel() {
    $('downloadPanel').style.display = 'none';
    $('progressBar').style.width = '0%';
    $('progressText').textContent = '0/0';
    $('progressLabel').textContent = '准备下载...';
  }

  function populateSources(sources) {
    const sel = $('sourceSelect');
    sel.innerHTML = '';
    sources.forEach(function(s) {
      const opt = document.createElement('option');
      opt.value = s.value;
      opt.textContent = s.label;
      sel.appendChild(opt);
    });
  }

  function applyConfig(config) {
    state.config = config;
    if (config.source) $('sourceSelect').value = config.source;
    if (config.search_type) $('typeSelect').value = config.search_type;
    if (config.bitrate) $('bitrateSelect').value = config.bitrate;
    if (config.number) $('numberInput').value = config.number;
    if (config.output_dir) $('outputDirInput').value = config.output_dir;
    $('coverCheck').checked = config.download_cover !== false;
    $('lyricCheck').checked = config.download_lyric !== false;
  }

  function collectConfig() {
    return {
      source: $('sourceSelect').value,
      search_type: $('typeSelect').value,
      bitrate: $('bitrateSelect').value,
      number: parseInt($('numberInput').value) || 20,
      output_dir: $('outputDirInput').value,
      download_cover: $('coverCheck').checked,
      download_lyric: $('lyricCheck').checked,
    };
  }

  function saveCurrentConfig() {
    if (window.pywebview && window.pywebview.api) {
      window.pywebview.api.save_config(collectConfig());
    }
  }

  function renderSongs(songs) {
    state.songs = songs;
    state.selectedIndices = new Set();
    const list = $('resultList');
    list.innerHTML = '';

    if (!songs || songs.length === 0) {
      list.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><p>未找到结果</p></div>';
      $('resultCount').textContent = '';
      return;
    }

    $('resultCount').textContent = '共 ' + songs.length + ' 首';

    songs.forEach(function(song, idx) {
      const item = document.createElement('div');
      item.className = 'song-item';
      item.dataset.index = idx;

      const check = document.createElement('input');
      check.type = 'checkbox';
      check.className = 'song-check';
      check.checked = false;
      check.addEventListener('change', function(e) {
        e.stopPropagation();
        if (e.target.checked) {
          state.selectedIndices.add(idx);
          item.classList.add('selected');
        } else {
          state.selectedIndices.delete(idx);
          item.classList.remove('selected');
        }
      });

      const cover = document.createElement('div');
      cover.className = 'song-cover';
      cover.textContent = '🎵';

      const info = document.createElement('div');
      info.className = 'song-info';
      const nameEl = document.createElement('div');
      nameEl.className = 'song-name';
      nameEl.textContent = song.name;
      if (song.source) {
        const tag = document.createElement('span');
        tag.className = 'source-tag';
        tag.textContent = song.source;
        nameEl.appendChild(tag);
      }
      const meta = document.createElement('div');
      meta.className = 'song-meta';
      meta.textContent = (song.artist || '未知') + ' · ' + (song.album || '未知') + ' · ' + (song.duration || '--:--');
      info.appendChild(nameEl);
      info.appendChild(meta);

      const dur = document.createElement('div');
      dur.className = 'song-duration';
      dur.textContent = song.duration || '--:--';

      const status = document.createElement('div');
      status.className = 'song-status';
      status.id = 'song-status-' + idx;

      item.appendChild(check);
      item.appendChild(cover);
      item.appendChild(info);
      item.appendChild(dur);
      item.appendChild(status);

      item.addEventListener('click', function(e) {
        if (e.target === check) return;
        check.checked = !check.checked;
        check.dispatchEvent(new Event('change'));
      });

      list.appendChild(item);
    });
  }

  function setSongStatus(idx, icon, cls) {
    const el = $('song-status-' + idx);
    if (el) {
      el.textContent = icon;
      el.className = 'song-status ' + (cls || '');
    }
  }

  async function init() {
    log('应用启动中...', 'info');

    if (!window.pywebview) {
      log('pywebview 未就绪，请在桌面窗口中运行', 'error');
      return;
    }

    try {
      const opts = await window.pywebview.api.get_valid_options();
      populateSources(opts.sources);

      const config = await window.pywebview.api.get_config();
      applyConfig(config);

      log('初始化完成，正在启动浏览器...', 'info');
      showLoading('正在启动浏览器并通过 Cloudflare 验证...');

      const result = await window.pywebview.api.init_browser();
      hideLoading();

      if (result.ready) {
        log('浏览器就绪，可以开始搜索', 'success');
      } else {
        log('浏览器初始化失败，请检查 Chrome 是否安装', 'error');
      }
    } catch (err) {
      hideLoading();
      log('初始化失败: ' + err, 'error');
    }

    bindEvents();
  }

  function bindEvents() {
    $('searchBtn').addEventListener('click', doSearch);
    $('searchInput').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') doSearch();
    });

    $('downloadSelectedBtn').addEventListener('click', doDownloadSelected);
    $('selectAllBtn').addEventListener('click', selectAll);
    $('deselectAllBtn').addEventListener('click', deselectAll);
    $('cancelDownloadBtn').addEventListener('click', cancelDownload);

    $('browseDirBtn').addEventListener('click', async function() {
      try {
        const path = await window.pywebview.api.select_directory();
        if (path) {
          $('outputDirInput').value = path;
          saveCurrentConfig();
        }
      } catch (err) {
        log('选择目录失败: ' + err, 'error');
      }
    });

    $('openDirBtn').addEventListener('click', function() {
      window.pywebview.api.open_download_dir($('outputDirInput').value);
    });

    $('envCheckBtn').addEventListener('click', showEnvCheck);
    $('closeEnvModal').addEventListener('click', function() {
      $('envModal').style.display = 'none';
    });

    $('toggleLogBtn').addEventListener('click', function() {
      state.logCollapsed = !state.logCollapsed;
      const panel = document.querySelector('.log-panel');
      panel.classList.toggle('collapsed', state.logCollapsed);
      $('toggleLogBtn').textContent = state.logCollapsed ? '展开' : '折叠';
    });

    $('sourceSelect').addEventListener('change', saveCurrentConfig);
    $('typeSelect').addEventListener('change', saveCurrentConfig);
    $('bitrateSelect').addEventListener('change', saveCurrentConfig);
    $('numberInput').addEventListener('change', saveCurrentConfig);
    $('coverCheck').addEventListener('change', saveCurrentConfig);
    $('lyricCheck').addEventListener('change', saveCurrentConfig);

    window.addEventListener('py-log', function(e) {
      log(e.detail.message, e.detail.level);
    });

    window.addEventListener('py-progress', function(e) {
      const d = e.detail;
      if (d.type === 'start') {
        showDownloadPanel();
        setProgress(0, d.total, '');
      } else if (d.type === 'progress') {
        setProgress(d.current, d.total, d.song_name);
        setSongStatus(d.current, '⬇', 'status-downloading');
      } else if (d.type === 'complete') {
        setProgress(d.success + d.fail + d.skip, d.success + d.fail + d.skip, '');
        setTimeout(function() { hideDownloadPanel(); }, 1500);
        state.currentTaskId = null;
      }
    });
  }

  async function doSearch() {
    const keyword = $('searchInput').value.trim();
    if (!keyword) {
      log('请输入搜索关键词', 'warn');
      return;
    }
    saveCurrentConfig();
    showLoading('正在搜索...');
    try {
      const source = $('sourceSelect').value;
      const type = $('typeSelect').value;
      const number = parseInt($('numberInput').value) || 20;
      const songs = await window.pywebview.api.search(keyword, source, type, number);
      renderSongs(songs);
    } catch (err) {
      log('搜索失败: ' + err, 'error');
    } finally {
      hideLoading();
    }
  }

  function selectAll() {
    state.songs.forEach(function(_, idx) {
      state.selectedIndices.add(idx);
    });
    document.querySelectorAll('.song-item').forEach(function(el) {
      el.classList.add('selected');
      const cb = el.querySelector('.song-check');
      if (cb) cb.checked = true;
    });
  }

  function deselectAll() {
    state.selectedIndices.clear();
    document.querySelectorAll('.song-item').forEach(function(el) {
      el.classList.remove('selected');
      const cb = el.querySelector('.song-check');
      if (cb) cb.checked = false;
    });
  }

  async function doDownloadSelected() {
    if (state.selectedIndices.size === 0) {
      log('请先选择要下载的歌曲', 'warn');
      return;
    }
    const selectedSongs = Array.from(state.selectedIndices).map(function(i) {
      return state.songs[i];
    });
    const config = collectConfig();
    log('开始下载 ' + selectedSongs.length + ' 首歌曲...', 'info');
    try {
      const taskId = await window.pywebview.api.start_download(
        selectedSongs,
        config.source,
        config.bitrate,
        config.download_lyric,
        config.download_cover,
        config.output_dir
      );
      state.currentTaskId = taskId;
      selectedSongs.forEach(function(s, i) {
        const idx = Array.from(state.selectedIndices)[i];
        setSongStatus(idx, '⏳', '');
      });
    } catch (err) {
      log('下载启动失败: ' + err, 'error');
    }
  }

  function cancelDownload() {
    if (state.currentTaskId) {
      window.pywebview.api.cancel_download(state.currentTaskId);
      log('正在取消下载...', 'warn');
    }
  }

  async function showEnvCheck() {
    showLoading('检查环境...');
    try {
      const results = await window.pywebview.api.check_environment();
      const body = $('envModalBody');
      body.innerHTML = '';
      results.forEach(function(r) {
        const item = document.createElement('div');
        item.className = 'env-item';
        item.innerHTML = '<div><div>' + r.name + '</div><div class="env-detail">' + r.detail + '</div></div>' +
          '<span class="' + (r.ok ? 'env-status-ok' : 'env-status-fail') + '">' + (r.ok ? '✓ 通过' : '✗ 失败') + '</span>';
        body.appendChild(item);
      });
      $('envModal').style.display = 'flex';
    } catch (err) {
      log('环境检查失败: ' + err, 'error');
    } finally {
      hideLoading();
    }
  }

  window.addEventListener('pywebviewready', init);
})();
```

- [ ] **Step 2: Verify file exists**

Run:
```powershell
Test-Path "f:\traeIde\music_downloader\gui\static\js\app.js"
```
Expected: `True`.

- [ ] **Step 3: Commit**

```bash
git add music_downloader/gui/static/js/app.js
git commit -m "feat(gui): add frontend JS logic - search, download, progress, settings"
```

---

## Task 8: Implement GUI Entry Point (app.py)

**Files:**
- Create: `music_downloader/gui/app.py`

- [ ] **Step 1: Create app.py**

Create `music_downloader/gui/app.py`:

```python
"""GUI application entry point.

Creates the pywebview window, loads the frontend, and starts the event loop.
"""

from __future__ import annotations

import os
import sys
from typing import Any


def _get_static_dir() -> str:
    """Resolve the static resources directory, compatible with Nuitka onefile builds."""
    if "__compiled__" in globals():
        base = os.path.dirname(os.path.abspath(sys.argv[0]))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "static")


def run_gui() -> None:
    """Start the desktop GUI application."""
    import webview

    from music_downloader.gui.api import MusicApi
    from music_downloader.gui.settings import load_config

    config = load_config()
    api = MusicApi()

    static_dir = _get_static_dir()
    html_path = os.path.join(static_dir, "index.html")

    if not os.path.exists(html_path):
        print(f"错误: 找不到 GUI 资源文件: {html_path}", file=sys.stderr)
        print("请确认 music_downloader/gui/static/ 目录存在且包含 index.html", file=sys.stderr)
        sys.exit(1)

    width = int(config.get("window_width", 960))
    height = int(config.get("window_height", 680))

    window = webview.create_window(
        title="音乐下载器",
        url=html_path,
        width=width,
        height=height,
        min_size=(800, 560),
        resizable=True,
        js_api=api,
        text_select=True,
    )
    api.set_window(window)

    def on_closing(window: Any) -> None:
        try:
            api.shutdown()
        except Exception:
            pass

    window.events.closing += on_closing

    webview.start(debug=False)
```

- [ ] **Step 2: Verify syntax**

Run:
```powershell
python -m py_compile music_downloader/gui/app.py
Write-Host "OK"
```
Expected: Prints "OK" with no errors.

- [ ] **Step 3: Quick import test**

Run:
```powershell
python -c "from music_downloader.gui.app import run_gui, _get_static_dir; d = _get_static_dir(); print('Static dir:', d); import os; print('index.html exists:', os.path.exists(os.path.join(d, 'index.html')))"
```
Expected: Prints static dir path and "index.html exists: True".

- [ ] **Step 4: Commit**

```bash
git add music_downloader/gui/app.py
git commit -m "feat(gui): add GUI entry point with pywebview window creation"
```

---

## Task 9: Modify CLI Entry to Support GUI Mode

**Files:**
- Modify: `music_downloader/cli.py`

- [ ] **Step 1: Add --gui argument to parse_args**

Read `music_downloader/cli.py` first to confirm current state, then modify the `advanced_group` section (around line 155-166) to add the `--gui` argument. The modified section should look like:

```python
    # ── 高级选项 ──
    advanced_group = parser.add_argument_group("高级选项")
    advanced_group.add_argument(
        "--check-env", action="store_true", help="检查本地依赖和 Google Chrome, 不访问音乐站点"
    )
    advanced_group.add_argument(
        "-i", "--interactive", action="store_true", help="交互模式, 浏览器保持运行可反复搜索"
    )
    advanced_group.add_argument(
        "--gui", action="store_true", help="启动桌面图形界面"
    )
    advanced_group.add_argument(
        "--user-data-dir",
        default=None,
        help="自定义 Chrome 用户数据目录 (默认在脚本同级 .chrome-profile/, 与系统 Chrome 隔离)",
    )
    return parser.parse_args(argv)
```

- [ ] **Step 2: Modify main() to detect GUI mode**

Modify the `main()` function at the bottom of `cli.py` (around line 581-589) to:

```python
def main(argv: Sequence[str] | None = None) -> None:
    """程序入口：解析参数后执行环境检查或主流程。"""
    args = parse_args(argv)
    if args.check_env:
        sys.exit(check_environment())

    # GUI mode: explicit --gui flag, or no arguments provided at all
    is_gui_mode = args.gui or (argv is None and len(sys.argv) <= 1)
    if is_gui_mode:
        from music_downloader.gui.app import run_gui
        run_gui()
        return

    return_code = run_with_browser(args)
    if return_code:
        sys.exit(return_code)
```

Note: When `argv` is `None` (default, i.e. user double-clicks exe or runs `python music_download.py`), `sys.argv` has only the script name (length 1), which triggers GUI mode. When any CLI arguments are passed (like `-k "周杰伦"`), CLI mode runs as before.

- [ ] **Step 3: Verify syntax**

Run:
```powershell
python -m py_compile music_downloader/cli.py
Write-Host "OK"
```
Expected: Prints "OK" with no errors.

- [ ] **Step 4: Verify CLI help includes --gui**

Run:
```powershell
python music_download.py --help 2>&1 | Select-String "gui"
```
Expected: Shows a line containing `--gui` in the help text.

- [ ] **Step 5: Verify existing CLI still works**

Run:
```powershell
python music_download.py --check-env
```
Expected: Environment check table displays, same behavior as before. (You don't need to pass Cloudflare; just verify it doesn't crash and shows the table.)

- [ ] **Step 6: Commit**

```bash
git add music_downloader/cli.py
git commit -m "feat(gui): add --gui flag; no-args launches GUI, existing CLI fully preserved"
```

---

## Task 10: Update Build Script for Nuitka

**Files:**
- Modify: `scripts/build_exe.ps1`

- [ ] **Step 1: Read current build script and update to include GUI static resources**

Read `scripts/build_exe.ps1` first, then add the `--include-data-dir` argument for GUI static files. The key change is adding this Nuitka flag somewhere in the Nuitka command arguments:

```powershell
--include-data-dir=music_downloader/gui/static=music_downloader/gui/static
```

If the existing script uses a variable or array for Nuitka arguments, add the include-data-dir there. After modification, the Nuitka command should include that flag so `music_downloader/gui/static/` is packaged inside the EXE and extracted to the correct relative path at runtime (which matches `_get_static_dir()` in app.py).

- [ ] **Step 2: Verify script syntax**

Run:
```powershell
powershell -Command "Get-Content scripts/build_exe.ps1 | Select-String 'include-data-dir'"
```
Expected: Shows a line containing the `--include-data-dir=music_downloader/gui/static` argument.

- [ ] **Step 3: Commit**

```bash
git add scripts/build_exe.ps1
git commit -m "feat(gui): update Nuitka build script to include GUI static resources"
```

---

## Task 11: Static Checks and Basic Verification

- [ ] **Step 1: Run ruff check**

Run:
```powershell
python -m ruff check music_downloader/gui/
```
Expected: No errors (or fix any issues that appear).

- [ ] **Step 2: Run mypy on new modules**

Run:
```powershell
python -m mypy music_downloader/gui/settings.py music_downloader/gui/api.py
```
Expected: No type errors (the bridge.py and app.py use `Any` for playwright/webview types which are set to `ignore_missing_imports`; if mypy complains, add appropriate type ignores or use `Any`).

- [ ] **Step 3: Run py_compile on all new files**

Run:
```powershell
python -m py_compile music_downloader/gui/__init__.py music_downloader/gui/settings.py music_downloader/gui/bridge.py music_downloader/gui/api.py music_downloader/gui/app.py
Write-Host "All files compile OK"
```
Expected: Prints "All files compile OK" with no errors.

- [ ] **Step 4: Verify pywebview is installed**

Run:
```powershell
pip install pywebview>=5.0
```
Expected: Installs successfully (or says requirement already satisfied).

- [ ] **Step 5: Test GUI launch (smoke test)**

Run:
```powershell
python music_download.py --gui
```
Expected: A desktop window opens showing the GUI with left sidebar (search box, music source selector, etc.) and empty main area. The browser initialization will proceed (may take a moment for Chrome to start and pass Cloudflare). Close the window after confirming it renders correctly.

- [ ] **Step 6: Commit any fixes needed**

If any fixes were needed during steps 1-5:
```bash
git add -A
git commit -m "fix(gui): resolve lint/type issues from static checks"
```

---

## Task 12: Final Verification (Manual End-to-End)

- [ ] **Step 1: Launch GUI by double-click / no-args**

Run:
```powershell
python music_download.py
```
Expected: GUI window opens (not CLI).

- [ ] **Step 2: Test search**

In the GUI: type "Beyond" in search box, click 搜索.
Expected: Results appear in the list after browser initializes.

- [ ] **Step 3: Test CLI mode still works**

Run:
```powershell
python music_download.py -k "Beyond" --search-only -n 3
```
Expected: CLI runs in terminal, shows results as before (no GUI window opens).

- [ ] **Step 4: Verify environment check**

Click 环境检查 button in GUI.
Expected: Modal appears showing Python version, playwright, mutagen, rich, Chrome status.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat(gui): desktop GUI with pywebview - complete implementation"
```
