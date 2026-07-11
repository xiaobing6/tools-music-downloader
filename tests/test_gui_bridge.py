from __future__ import annotations

from pathlib import Path
from typing import Any

from music_downloader.gui import bridge as bridge_module
from music_downloader.gui.bridge import DownloadTask, MusicBridge


class _InlineSession:
    page: object = object()
    context: object = object()

    def submit(self, func, timeout: float | None = None) -> Any:  # noqa: ANN001
        return func()


class _FakePage:
    def goto(self, *_args: object, **_kwargs: object) -> None:
        return None


class _FakeContext:
    def __init__(self) -> None:
        self.pages = [_FakePage()]
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _FakeChromium:
    def __init__(self, calls: list[dict[str, object]]) -> None:
        self.calls = calls

    def launch_persistent_context(self, **kwargs: object) -> _FakeContext:
        self.calls.append(kwargs)
        return _FakeContext()


class _FakePlaywright:
    def __init__(self, calls: list[dict[str, object]]) -> None:
        self.chromium = _FakeChromium(calls)


def test_gui_browser_hides_only_headless_platform_window(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    cloudflare_results = iter([False, True])
    session = bridge_module._PlaywrightThread()
    session._playwright = _FakePlaywright(calls)
    monkeypatch.setattr(session, "submit", lambda func, timeout=None: func())
    monkeypatch.setattr(
        bridge_module,
        "wait_for_cloudflare",
        lambda _page: next(cloudflare_results),
    )

    assert session.start_browser(headless=True, user_data_dir=str(tmp_path)) is True
    assert calls[0]["headless"] is True
    assert calls[0]["args"] == ["--window-position=-32000,-32000"]
    assert calls[1]["headless"] is False
    assert calls[1]["args"] == []


def test_download_event_includes_failure_reason_and_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events: list[dict[str, Any]] = []
    bridge = MusicBridge(on_progress=events.append)
    bridge._session = _InlineSession()  # type: ignore[assignment]
    monkeypatch.setattr(bridge_module, "download_song", lambda **_kwargs: "fail")

    task = DownloadTask(
        task_id="task-1",
        songs=[{"id": "1", "name": "Song", "artist": "Artist"}],
        source="netease",
        bitrate="320",
        download_lyric=True,
        download_cover=True,
        output_dir=str(tmp_path),
    )

    bridge._run_download(task)

    done_event = next(event for event in events if event["type"] == "song_done")
    assert done_event["result"] == "fail"
    assert done_event["reason"]
    assert done_event["path"].endswith(".mp3")


def test_download_event_uses_original_gui_index(
    tmp_path: Path,
    monkeypatch,
) -> None:
    events: list[dict[str, Any]] = []
    bridge = MusicBridge(on_progress=events.append)
    bridge._session = _InlineSession()  # type: ignore[assignment]
    monkeypatch.setattr(bridge_module, "download_song", lambda **_kwargs: "skip")

    task = DownloadTask(
        task_id="task-1",
        songs=[{"id": "8", "name": "Song", "artist": "Artist", "_gui_index": 7}],
        source="netease",
        bitrate="320",
        download_lyric=True,
        download_cover=True,
        output_dir=str(tmp_path),
    )

    bridge._run_download(task)

    done_event = next(event for event in events if event["type"] == "song_done")
    assert done_event["index"] == 7


def test_gui_download_uses_keyword_directory_like_cli(
    tmp_path: Path,
    monkeypatch,
) -> None:
    save_dirs: list[str] = []
    bridge = MusicBridge()
    bridge._session = _InlineSession()  # type: ignore[assignment]

    def fake_download_song(**kwargs: Any) -> str:
        save_dirs.append(str(kwargs["save_dir"]))
        return "success"

    monkeypatch.setattr(bridge_module, "download_song", fake_download_song)

    task = DownloadTask(
        task_id="task-1",
        keyword="周杰伦",
        songs=[{"id": "1", "name": "晴天", "artist": "第一首歌手"}],
        source="netease",
        bitrate="320",
        download_lyric=True,
        download_cover=True,
        output_dir=str(tmp_path),
    )

    bridge._run_download(task)

    assert save_dirs == [str(tmp_path / "周杰伦")]
    assert not (tmp_path / "第一首歌手").exists()
