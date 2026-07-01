"""Encoding helpers for upstream API requests."""

from __future__ import annotations

import urllib.parse


def url_encode(value: str) -> str:
    """URL-encode a value without preserving safe characters."""
    return urllib.parse.quote(value, safe="")
