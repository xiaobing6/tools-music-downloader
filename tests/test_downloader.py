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


def test_download_song_cleans_up_when_embed_metadata_fails(monkeypatch):
    test_dir = make_test_dir()
    try:
        monkeypatch.setattr(downloader, "get_play_url", lambda *_args, **_kwargs: "audio.mp3")
        monkeypatch.setattr(downloader, "get_lyric", lambda *_args, **_kwargs: "")
        monkeypatch.setattr(downloader, "get_pic_url", lambda *_args, **_kwargs: "")

        def boom(**_kwargs):
            raise RuntimeError("mutagen is angry")

        monkeypatch.setattr(downloader, "embed_metadata", boom)
        monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)

        context = FakeContext(
            [FakeResponse(ok=True, body=b"x" * 11000, headers={"content-length": "11000"})]
        )
        song = {"id": "1", "artist": "Artist", "name": "Song"}

        result = downloader.download_song(
            None, context, song, "netease", "2026.5.10", str(test_dir)
        )

        # 元数据失败 → 残缺文件应被清理 + 返回 fail
        assert result == "fail"
        assert not (test_dir / "[1] Artist - Song.mp3").exists()
    finally:
        remove_test_dir(test_dir)


def test_download_song_handles_replace_oserror(monkeypatch):
    test_dir = make_test_dir()
    try:
        monkeypatch.setattr(downloader, "get_play_url", lambda *_args, **_kwargs: "audio.mp3")
        monkeypatch.setattr(downloader, "get_lyric", lambda *_args, **_kwargs: "")
        monkeypatch.setattr(downloader, "get_pic_url", lambda *_args, **_kwargs: "")
        monkeypatch.setattr(downloader, "embed_metadata", lambda **_k: None)
        monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)

        # 第一次 os.replace 抛 OSError（模拟跨盘），第二次允许正常进行
        original_replace = downloader.os.replace
        calls = {"n": 0}

        def fake_replace(src, dst):
            calls["n"] += 1
            if calls["n"] == 1:
                raise OSError(17, "The system cannot move the file to a different disk drive.")
            return original_replace(src, dst)

        monkeypatch.setattr(downloader.os, "replace", fake_replace)

        # 第二次下载时还要求成功文件 size
        context = FakeContext(
            [
                FakeResponse(ok=True, body=b"x" * 11000, headers={"content-length": "11000"}),
                FakeResponse(ok=True, body=b"y" * 11000, headers={"content-length": "11000"}),
            ]
        )
        song = {"id": "1", "artist": "Artist", "name": "Song"}

        result = downloader.download_song(
            None, context, song, "netease", "2026.5.10", str(test_dir)
        )

        assert result == "success"
        assert calls["n"] == 2
    finally:
        remove_test_dir(test_dir)


def test_download_song_logs_cover_failure(monkeypatch, capsys):
    test_dir = make_test_dir()
    try:
        monkeypatch.setattr(downloader, "get_play_url", lambda *_args, **_kwargs: "audio.mp3")
        monkeypatch.setattr(downloader, "get_lyric", lambda *_args, **_kwargs: "")
        monkeypatch.setattr(downloader, "get_pic_url", lambda *_args, **_kwargs: "http://pic")
        monkeypatch.setattr(downloader, "embed_metadata", lambda **_k: None)
        monkeypatch.setattr(downloader.time, "sleep", lambda _seconds: None)

        context = FakeContext(
            [
                FakeResponse(ok=True, body=b"x" * 11000, headers={"content-length": "11000"}),
                FakeResponse(ok=False, status=404),  # 封面失败
            ]
        )
        song = {"id": "1", "artist": "Artist", "name": "Song"}

        result = downloader.download_song(
            None, context, song, "netease", "2026.5.10", str(test_dir)
        )
        captured = capsys.readouterr()

        assert result == "success"
        assert "封面下载失败" in captured.out
    finally:
        remove_test_dir(test_dir)


def test_cleanup_paths_supports_directories(monkeypatch):
    test_dir = make_test_dir()
    try:
        target = test_dir / "sub"
        target.mkdir()
        (target / "inner.txt").write_text("x")
        downloader.cleanup_paths([str(target)])
        assert not target.exists()
    finally:
        remove_test_dir(test_dir)


def test_cleanup_paths_handles_missing_and_empty():
    downloader.cleanup_paths(None)
    downloader.cleanup_paths([])
    downloader.cleanup_paths(["/non/existent/file"])
    # 不应抛异常
