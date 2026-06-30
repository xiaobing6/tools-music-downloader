"""Compatibility wrapper for the GdStudio API client."""

from music_downloader.infrastructure.gdstudio import (
    GdStudioClient,
    compute_signature,
    fetch_api,
    fetch_with_cf_retry,
    get_lyric,
    get_pic_url,
    get_play_url,
    refresh_cloudflare,
    search_with_pagination,
    wait_for_cloudflare,
)

__all__ = [
    "GdStudioClient",
    "compute_signature",
    "fetch_api",
    "fetch_with_cf_retry",
    "get_lyric",
    "get_pic_url",
    "get_play_url",
    "refresh_cloudflare",
    "search_with_pagination",
    "wait_for_cloudflare",
]
