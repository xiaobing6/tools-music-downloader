"""Typed exceptions for downloader domain and service failures."""

from __future__ import annotations


class MusicDownloaderError(Exception):
    """Base exception for music downloader failures."""


class BrowserStartupError(MusicDownloaderError):
    """Raised when Chrome or Playwright cannot start."""


class CloudflareError(MusicDownloaderError):
    """Raised when Cloudflare clearance cannot be obtained or reused."""


class ApiRequestError(MusicDownloaderError):
    """Raised when the music API request fails."""


class DownloadError(MusicDownloaderError):
    """Raised when audio download or persistence fails."""
