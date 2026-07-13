from __future__ import annotations

from pathlib import Path

import pytest

from music_downloader.infrastructure.downloader import _download_body_to_file


class _FakeResponse:
    def __init__(self, content_type: str, body: bytes) -> None:
        self.ok = True
        self.status = 200
        self.headers = {
            "content-type": content_type,
            "content-length": str(len(body)),
        }
        self._body = body

    def body(self) -> bytes:
        return self._body


class _FakeRequest:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response

    def get(self, _url: str, *, timeout: int) -> _FakeResponse:
        assert timeout > 0
        return self._response


class _FakeContext:
    def __init__(self, response: _FakeResponse) -> None:
        self.request = _FakeRequest(response)


def _download(tmp_path: Path, content_type: str, body: bytes) -> bool:
    return _download_body_to_file(
        _FakeContext(_FakeResponse(content_type, body)),
        "https://example.test/audio",
        tmp_path / "song.mp3.tmp",
        tmp_path / "song.mp3",
    )


@pytest.mark.parametrize(
    "content_type",
    [
        "text/html; charset=utf-8",
        "application/json",
        "application/problem+json",
        "application/xml",
        "text/xml; charset=utf-8",
        "application/problem+xml",
    ],
)
def test_download_rejects_explicit_error_document_types(
    tmp_path: Path,
    content_type: str,
) -> None:
    body = b"not audio" + b"x" * 12_000

    assert _download(tmp_path, content_type, body) is False
    assert not (tmp_path / "song.mp3").exists()
    assert not (tmp_path / "song.mp3.tmp").exists()


@pytest.mark.parametrize(
    "body",
    [
        b"\xef\xbb\xbf  <!DOCTYPE html><html>error</html>" + b"x" * 12_000,
        b' \r\n {"error": "denied"}' + b"x" * 12_000,
        b'\t["error"]' + b"x" * 12_000,
        b'\n<?xml version="1.0"?><error />' + b"x" * 12_000,
    ],
)
def test_download_sniffs_error_documents_with_unknown_mime(
    tmp_path: Path,
    body: bytes,
) -> None:
    assert _download(tmp_path, "application/x-download", body) is False
    assert not (tmp_path / "song.mp3").exists()


@pytest.mark.parametrize(
    "content_type",
    ["audio/mpeg", "application/octet-stream", "", "application/x-download"],
)
def test_download_accepts_conservative_binary_responses(
    tmp_path: Path,
    content_type: str,
) -> None:
    body = b"ID3" + b"\x00" * 12_000

    assert _download(tmp_path, content_type, body) is True
    assert (tmp_path / "song.mp3").read_bytes() == body


def test_rejected_response_does_not_replace_existing_file(tmp_path: Path) -> None:
    final_path = tmp_path / "song.mp3"
    final_path.write_bytes(b"existing audio")
    body = b"<html>upstream error</html>" + b"x" * 12_000

    assert _download(tmp_path, "text/html", body) is False
    assert final_path.read_bytes() == b"existing audio"
