from __future__ import annotations

from pathlib import Path
from typing import Any

from music_downloader.domain.models import Song
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


def test_gui_search_returns_before_progressive_cover_resolution(monkeypatch) -> None:
    captured: list[tuple[list[Song], str, int]] = []

    class FakeClient:
        def __init__(self, _page: object) -> None:
            pass

        def search(self, _options: object) -> list[dict[str, object]]:
            return [
                {
                    "id": "1",
                    "name": "Song",
                    "artist": ["Artist"],
                    "source": "netease",
                    "pic_id": "pic-1",
                    "extra_data": {"duration": 61},
                }
            ]

    bridge = MusicBridge(on_cover=lambda _detail: None)
    bridge._session = _InlineSession()  # type: ignore[assignment]
    monkeypatch.setattr(bridge, "ensure_browser", lambda: True)
    monkeypatch.setattr(bridge_module, "GdStudioClient", FakeClient)
    monkeypatch.setattr(
        bridge,
        "_start_cover_resolution",
        lambda songs, source, generation: captured.append((songs, source, generation)),
    )

    results = bridge.search("Song", "netease", "song", 1)

    assert "cover" not in results[0]
    assert captured[0][0][0].pic_id == "pic-1"
    assert captured[0][1] == "netease"


def test_cover_resolution_continues_after_one_song_fails(monkeypatch) -> None:
    events: list[dict[str, str]] = []

    class FakeClient:
        def __init__(self, _page: object) -> None:
            pass

        def get_pic_url(self, song: Song, _source: str) -> str:
            if song.id == "2":
                raise RuntimeError("cover failed")
            return f"https://covers.example/{song.id}.jpg"

    bridge = MusicBridge(on_cover=events.append)
    bridge._session = _InlineSession()  # type: ignore[assignment]
    bridge._cover_generation = 1
    monkeypatch.setattr(bridge_module, "GdStudioClient", FakeClient)

    bridge._resolve_covers(
        [Song(id="1", pic_id="p1"), Song(id="2", pic_id="p2"), Song(id="3", pic_id="p3")],
        "netease",
        1,
    )

    assert [event["id"] for event in events] == ["1", "3"]


def test_cover_resolution_stops_when_generation_changes(monkeypatch) -> None:
    events: list[dict[str, str]] = []
    requested: list[str] = []

    class FakeClient:
        def __init__(self, _page: object) -> None:
            pass

        def get_pic_url(self, song: Song, _source: str) -> str:
            requested.append(song.id)
            return f"https://covers.example/{song.id}.jpg"

    bridge = MusicBridge()
    bridge._session = _InlineSession()  # type: ignore[assignment]
    bridge._cover_generation = 1

    def handle_cover(detail: dict[str, str]) -> None:
        events.append(detail)
        bridge._cover_generation = 2

    bridge._on_cover = handle_cover
    monkeypatch.setattr(bridge_module, "GdStudioClient", FakeClient)

    bridge._resolve_covers(
        [Song(id="1", pic_id="p1"), Song(id="2", pic_id="p2")],
        "netease",
        1,
    )

    assert requested == ["1"]
    assert [event["id"] for event in events] == ["1"]
