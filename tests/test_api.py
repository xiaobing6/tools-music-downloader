import json

import pytest

import music_downloader.api as api
from music_downloader.utils import url_encode


class FakeContext:
    def __init__(self, cookies=None):
        # 注意：必须用 `is None` 判别，允许外部显式传空列表模拟"无 cookie"
        self._cookies = [{"name": "cf_clearance", "value": "ok"}] if cookies is None else cookies

    def cookies(self):
        return list(self._cookies)


class FakePage:
    def __init__(self, cookies=None):
        self.context = FakeContext(cookies)


def test_compute_signature_is_stable():
    encoded = url_encode("Beyond")
    assert (
        api.compute_signature("music.gdstudio.org", "2026.5.10", "1760000000000", encoded)
        == "74A9ECA5"
    )


def test_compute_signature_rejects_empty_version():
    with pytest.raises(ValueError, match="version is required"):
        api.compute_signature("music.gdstudio.org", "", "1760000000000", "x")


def test_wait_for_cloudflare_detects_cookie():
    assert api.wait_for_cloudflare(FakePage()) is True


def test_wait_for_cloudflare_fails_when_cookie_missing():
    page = FakePage(cookies=[])
    calls = {"n": 0}

    def fake_reload(*_args, **_kwargs):
        calls["n"] += 1

    page.reload = fake_reload  # type: ignore[attr-defined]

    result = api.wait_for_cloudflare(page, max_retries=2)
    # max_retries=2：第一轮拿到 cookie？否 → reload；第二轮再判 → 仍否；不 reload
    assert result is False
    assert calls["n"] == 1  # 只在中间那次 reload，最后一次不 reload


def test_search_with_pagination_fetches_multiple_pages(monkeypatch):
    calls = []

    def fake_timestamp(_page):
        return "1760000000000"

    def fake_fetch(_page, body):
        calls.append(body)
        if "pages=1" in body:
            return 200, json.dumps([{"id": str(index)} for index in range(99)])
        return 200, json.dumps([{"id": "99"}, {"id": "100"}])

    monkeypatch.setattr(api, "get_timestamp", fake_timestamp)
    monkeypatch.setattr(api, "fetch_api", fake_fetch)

    results = api.search_with_pagination(FakePage(), "Beyond", "netease", "song", 101, "2026.5.10")

    assert len(results) == 101
    assert len(calls) == 2
    assert "count=99" in calls[0]
    assert "count=2" in calls[1]


def test_search_with_pagination_stops_on_invalid_json(monkeypatch):
    monkeypatch.setattr(api, "get_timestamp", lambda _page: "1760000000000")
    monkeypatch.setattr(api, "fetch_api", lambda _page, _body: (200, "not-json"))

    assert api.search_with_pagination(FakePage(), "Beyond", "netease", "song", 5, "2026.5.10") == []


def test_search_with_pagination_returns_empty_on_502(monkeypatch):
    monkeypatch.setattr(api, "get_timestamp", lambda _page: "1760000000000")
    monkeypatch.setattr(api, "fetch_api", lambda _page, _body: (502, "bad gateway"))

    results = api.search_with_pagination(FakePage(), "Beyond", "netease", "song", 5, "2026.5.10")
    assert results == []


def test_search_with_pagination_breaks_on_empty_data(monkeypatch):
    monkeypatch.setattr(api, "get_timestamp", lambda _page: "1760000000000")
    monkeypatch.setattr(api, "fetch_api", lambda _page, _body: (200, "[]"))

    assert api.search_with_pagination(FakePage(), "Beyond", "netease", "song", 5, "2026.5.10") == []


def test_signed_get_succeeds_first_try(monkeypatch):
    monkeypatch.setattr(api, "fetch_api", lambda _p, _b: (200, "ok"))
    status, text = api._signed_get(FakePage(), "body=x", "资源")
    assert status == 200
    assert text == "ok"


def test_signed_get_recovers_after_403(monkeypatch):
    calls = {"n": 0}

    def fake_fetch(_p, _b):
        calls["n"] += 1
        if calls["n"] == 1:
            return 403, ""
        return 200, "recovered"

    monkeypatch.setattr(api, "fetch_api", fake_fetch)
    monkeypatch.setattr(api, "refresh_cloudflare", lambda _p: True)

    status, text = api._signed_get(FakePage(), "body=x", "资源")
    assert status == 200
    assert text == "recovered"
    assert calls["n"] == 2


def test_signed_get_gives_up_when_refresh_fails(monkeypatch):
    monkeypatch.setattr(api, "fetch_api", lambda _p, _b: (403, ""))
    monkeypatch.setattr(api, "refresh_cloudflare", lambda _p: False)

    status, text = api._signed_get(FakePage(), "body=x", "资源")
    assert status == 403
    assert text == ""


def test_get_play_url_empty_when_no_id(monkeypatch):
    monkeypatch.setattr(api, "get_timestamp", lambda _p: "1")
    assert api.get_play_url(FakePage(), {"id": ""}, "netease", "2026.5.10") == ""


def test_get_play_url_returns_url(monkeypatch):
    monkeypatch.setattr(api, "get_timestamp", lambda _p: "1760000000000")
    monkeypatch.setattr(api, "_signed_url_get", lambda _p, _b, _name: "https://x/audio.mp3")
    url = api.get_play_url(FakePage(), {"id": "42"}, "netease", "2026.5.10")
    assert url == "https://x/audio.mp3"


def test_get_lyric_empty_when_no_id(monkeypatch):
    monkeypatch.setattr(api, "get_timestamp", lambda _p: "1")
    assert api.get_lyric(FakePage(), {"lyric_id": ""}, "netease", "2026.5.10") == ""


def test_get_pic_url_empty_when_no_id(monkeypatch):
    monkeypatch.setattr(api, "get_timestamp", lambda _p: "1")
    assert api.get_pic_url(FakePage(), {"pic_id": ""}, "netease", "2026.5.10") == ""


def test_get_lyric_returns_lyric_text(monkeypatch):
    monkeypatch.setattr(api, "get_timestamp", lambda _p: "1760000000000")
    monkeypatch.setattr(
        api, "_signed_get", lambda _p, _b, _name: (200, json.dumps({"lyric": "[00:00]hi"}))
    )
    text = api.get_lyric(FakePage(), {"lyric_id": "1"}, "netease", "2026.5.10")
    assert text == "[00:00]hi"
