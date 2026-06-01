import os
import shutil
from pathlib import Path
from uuid import uuid4

import music_downloader.downloader as downloader


class FakeResponse:
    def __init__(self, ok=True, status=200, body=b"", headers=None):
        self.ok = ok
        self.status = status
        self._body = body
        self.headers = headers or {}

    def body(self):
        return self._body


class FakeRequest:
    def __init__(self, responses):
        self.responses = list(responses)
        self.urls = []

    def get(self, url, timeout):
        self.urls.append((url, timeout))
        return self.responses.pop(0)


class FakeContext:
    def __init__(self, responses):
        self.request = FakeRequest(responses)


def make_test_dir():
    path = Path(__file__).resolve().parent / "_runtime" / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def remove_test_dir(path):
    shutil.rmtree(str(path), ignore_errors=True)


def test_build_output_path_uses_flac_extension():
    test_dir = make_test_dir()
    try:
        song = {"id": "1", "artist": "A/B", "name": "Song"}
        path = downloader.build_output_path(str(test_dir), song, "flac")
        assert path.endswith("[1] A_B - Song.flac")
    finally:
        remove_test_dir(test_dir)


def test_download_song_retries_short_file_then_succeeds(monkeypatch):
    test_dir = make_test_dir()
    song = {"id": "1", "artist": "A/B", "name": "Song"}
    try:
        monkeypatch.setattr(downloader, "get_play_url", lambda *_args, **_kwargs: "audio.mp3")
        monkeypatch.setattr(downloader, "get_lyric", lambda *_args, **_kwargs: "")
        monkeypatch.setattr(downloader, "get_pic_url", lambda *_args, **_kwargs: "")
        monkeypatch.setattr(downloader, "embed_metadata", lambda *_args, **_kwargs: None)
        monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)

        context = FakeContext(
            [
                FakeResponse(ok=True, body=b"too-short"),
                FakeResponse(ok=True, body=b"x" * 11000, headers={"content-length": "11000"}),
            ]
        )
        song = {"id": "1", "artist": "Artist", "name": "Song"}

        result = downloader.download_song(
            None, context, song, "netease", "2026.5.10", str(test_dir)
        )

        assert result == "success"
        assert len(context.request.urls) == 2
        assert os.path.exists(test_dir / "[1] Artist - Song.mp3")
    finally:
        remove_test_dir(test_dir)


def test_download_song_retries_http_failure(monkeypatch):
    test_dir = make_test_dir()
    try:
        monkeypatch.setattr(downloader, "get_play_url", lambda *_args, **_kwargs: "audio.mp3")
        monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)

        context = FakeContext(
            [
                FakeResponse(ok=False, status=500),
                FakeResponse(ok=False, status=500),
            ]
        )
        song = {"id": "1", "artist": "Artist", "name": "Song"}

        result = downloader.download_song(
            None, context, song, "netease", "2026.5.10", str(test_dir)
        )

        assert result == "fail"
        assert len(context.request.urls) == 2
    finally:
        remove_test_dir(test_dir)


def test_download_song_skips_existing_file(monkeypatch):
    test_dir = make_test_dir()
    try:
        song = {"id": "1", "artist": "Artist", "name": "Song"}
        output = test_dir / "[1] Artist - Song.mp3"
        output.write_bytes(b"exists")
        monkeypatch.setattr(downloader, "get_play_url", lambda *_args, **_kwargs: "audio.mp3")

        result = downloader.download_song(
            None, FakeContext([]), song, "netease", "2026.5.10", str(test_dir)
        )

        assert result == "skip"
    finally:
        remove_test_dir(test_dir)
