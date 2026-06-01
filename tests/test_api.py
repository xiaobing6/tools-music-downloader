import json

import music_downloader.api as api
from music_downloader.utils import url_encode


class FakeContext:
    def cookies(self):
        return [{"name": "cf_clearance", "value": "ok"}]


class FakePage:
    context = FakeContext()


def test_compute_signature_is_stable():
    encoded = url_encode("Beyond")
    assert api.compute_signature("music.gdstudio.org", "2026.5.10", "1760000000000", encoded) == "74A9ECA5"


def test_wait_for_cloudflare_detects_cookie():
    assert api.wait_for_cloudflare(FakePage()) is True


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
