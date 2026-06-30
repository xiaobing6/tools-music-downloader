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
