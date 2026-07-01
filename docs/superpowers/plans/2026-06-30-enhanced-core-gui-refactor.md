# Enhanced Core and GUI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the project into a typed shared core used by both CLI and GUI, while preserving the existing user-facing CLI/GUI forms and improving GUI download feedback.

**Architecture:** Introduce Pydantic domain models, shared infrastructure adapters, and application services. Keep `music_download.py` as the single executable entrypoint, keep pywebview as the GUI shell, and preserve compatibility wrappers while moving implementation into `domain/`, `infrastructure/`, `services/`, and `adapters/`.

**Tech Stack:** Python 3.10+, Playwright sync API, mutagen, rich, pywebview, Typer, Pydantic v2, pytest, Nuitka.

---

## Scope Check

This is a single coherent refactor because CLI and GUI currently duplicate the same browser, search, and download workflow. The plan is split so every task produces a runnable project state, with tests added before behavior changes where practical.

## File Structure

- Create `music_downloader/domain/enums.py`: typed string enums for sources, search types, formats, bitrates, and download statuses.
- Create `music_downloader/domain/models.py`: Pydantic models for songs, options, settings, progress events, and results.
- Create `music_downloader/domain/errors.py`: explicit exception types and user-facing error reasons.
- Create `music_downloader/infrastructure/files.py`: path resolution, filename sanitizing, output path construction, and existence checks.
- Create `music_downloader/infrastructure/metadata.py`: warning-oriented metadata writer wrapper.
- Create `music_downloader/infrastructure/gdstudio.py`: typed API client extracted from current `api.py`.
- Create `music_downloader/infrastructure/browser.py`: shared Playwright persistent context management.
- Create `music_downloader/infrastructure/environment.py`: typed environment checks extracted from current `env.py`.
- Create `music_downloader/services/search.py`: shared search, pagination, dedupe, and normalization.
- Create `music_downloader/services/download.py`: shared single-song and batch download service.
- Create `music_downloader/adapters/cli/legacy.py`: temporary home for the existing argparse workflow while Typer becomes the public entrypoint.
- Create `music_downloader/adapters/cli/app.py`: Typer CLI entrypoint.
- Create `music_downloader/adapters/cli/interactive.py`: interactive command loop and parser.
- Create `music_downloader/adapters/cli/display.py`: CLI result rendering.
- Keep `music_downloader/cli.py`, `api.py`, `downloader.py`, `env.py`, `display.py`, and `metadata.py` as thin compatibility wrappers until all local imports are migrated.
- Modify `music_downloader/gui/api.py`, `music_downloader/gui/bridge.py`, `music_downloader/gui/settings.py`, and `music_downloader/gui/static/js/app.js` to use shared services and default-only settings.
- Modify `requirements.txt`, `requirements-dev.txt`, `pyproject.toml`, `README.md`, and `AGENTS.md`.
- Create `tests/` with focused tests for models, files, download semantics, CLI options, GUI API defaults, and service orchestration.

---

### Task 1: Dependency And Test Harness

**Files:**
- Modify: `requirements.txt`
- Modify: `requirements-dev.txt`
- Modify: `pyproject.toml`
- Create: `tests/__init__.py`
- Create: `tests/test_imports.py`

- [ ] **Step 1: Add dependency declarations**

Update `requirements.txt` so it contains exactly:

```text
# -*-coding:utf-8 -*-
playwright>=1.45
mutagen>=1.47
rich>=13
rich-argparse>=1.8
typer>=0.12
pydantic>=2.7
pywebview>=5.0
```

Update `requirements-dev.txt` so it contains exactly:

```text
-r requirements.txt
ruff>=0.5
mypy>=1.10
pytest>=8.2
```

In `pyproject.toml`, update `[project].dependencies` to include `typer>=0.12`, `pydantic>=2.7`, and `pywebview>=5.0`. Keep `rich-argparse>=1.8` in both `requirements.txt` and `pyproject.toml` during this task because the current `music_downloader/cli.py` still imports it. Remove `rich-argparse` in Task 11 after Typer is the public CLI entrypoint and no local imports remain.

- [ ] **Step 2: Add a pytest smoke test**

Create `tests/__init__.py` as an empty file.

Create `tests/test_imports.py`:

```python
from __future__ import annotations


def test_package_imports() -> None:
    import music_downloader

    assert music_downloader is not None
```

- [ ] **Step 3: Run the smoke test before adding new code**

Run:

```powershell
python -m pytest tests/test_imports.py -q
```

Expected before dependencies are installed: either `1 passed` if pytest is available, or `No module named pytest`. If pytest is missing, run dependency installation outside this plan step before continuing.

- [ ] **Step 4: Run static import checks**

Run:

```powershell
python -m py_compile music_download.py
```

Expected: command exits with code 0 and prints no output.

- [ ] **Step 5: Commit**

```powershell
git add requirements.txt requirements-dev.txt pyproject.toml tests/__init__.py tests/test_imports.py
git commit -m "chore: add typed refactor dependencies and test harness"
```

---

### Task 2: Domain Models

**Files:**
- Create: `music_downloader/domain/__init__.py`
- Create: `music_downloader/domain/enums.py`
- Create: `music_downloader/domain/models.py`
- Create: `music_downloader/domain/errors.py`
- Create: `tests/test_domain_models.py`

- [ ] **Step 1: Write failing domain model tests**

Create `tests/test_domain_models.py`:

```python
from __future__ import annotations

import pytest
from pydantic import ValidationError

from music_downloader.domain.enums import Bitrate, DownloadStatus, SearchType, Source
from music_downloader.domain.models import DownloadResult, SearchOptions, Song


def test_song_accepts_legacy_api_dict() -> None:
    song = Song.from_api(
        {
            "id": 123,
            "url_id": "u-1",
            "pic_id": "p-1",
            "lyric_id": "l-1",
            "name": "Track",
            "artist": ["A", "B"],
            "album": "Album",
            "duration": 125,
            "source": "netease",
            "has_hires": True,
        }
    )

    assert song.id == "123"
    assert song.artist == "A, B"
    assert song.display_name == "Track [Hi-Res]"
    assert song.duration_text == "2:05"


def test_search_options_validate_values() -> None:
    options = SearchOptions(keyword="Beyond", source=Source.NETEASE, search_type=SearchType.SONG)

    assert options.keyword == "Beyond"
    assert options.source == Source.NETEASE


def test_search_options_reject_invalid_number() -> None:
    with pytest.raises(ValidationError):
        SearchOptions(keyword="Beyond", number=0)


def test_download_result_records_warning_success() -> None:
    result = DownloadResult(
        song=Song(id="1", name="Song"),
        status=DownloadStatus.SUCCESS,
        path="downloads/Song.mp3",
        warnings=["ID3 标签写入失败"],
    )

    assert result.ok is True
    assert result.warnings == ["ID3 标签写入失败"]


def test_bitrate_values_match_cli() -> None:
    assert [item.value for item in Bitrate] == ["128", "192", "320", "flac"]
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest tests/test_domain_models.py -q
```

Expected: FAIL because `music_downloader.domain` does not exist yet.

- [ ] **Step 3: Add enum definitions**

Create `music_downloader/domain/__init__.py`:

```python
"""Typed domain models for the music downloader."""
```

Create `music_downloader/domain/enums.py`:

```python
"""Shared typed values used by CLI, GUI, and services."""

from __future__ import annotations

from enum import Enum


class Source(str, Enum):
    NETEASE = "netease"
    MIGU = "migu"
    KUWO = "kuwo"
    YTMUSIC = "ytmusic"
    TIDAL = "tidal"
    QOBUZ = "qobuz"
    DEEZER = "deezer"
    SPOTIFY = "spotify"
    TENCENT = "tencent"
    XIMALAYA = "ximalaya"
    JOOX = "joox"
    APPLE = "apple"


class SearchType(str, Enum):
    SONG = "song"
    ALBUM = "album"
    PLAYLIST = "playlist"


class OutputFormat(str, Enum):
    TABLE = "table"
    JSON = "json"
    LIST = "list"


class Bitrate(str, Enum):
    MP3_128 = "128"
    MP3_192 = "192"
    MP3_320 = "320"
    FLAC = "flac"


class DownloadStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    SKIP = "skip"
    FAIL = "fail"
    CANCELLED = "cancelled"
```

- [ ] **Step 4: Add domain models**

Create `music_downloader/domain/models.py`:

```python
"""Pydantic domain models shared by CLI, GUI, and services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from music_downloader.config import DEFAULT_BITRATE, DEFAULT_KEYWORD, DEFAULT_NUMBER, DEFAULT_SOURCE
from music_downloader.domain.enums import Bitrate, DownloadStatus, OutputFormat, SearchType, Source
from music_downloader.utils import format_duration, get_artist_str


class Song(BaseModel):
    model_config = ConfigDict(use_enum_values=False)

    id: str = ""
    url_id: str = ""
    pic_id: str = ""
    lyric_id: str = ""
    name: str = "未知"
    artist: str = "未知"
    album: str = "未知"
    duration: int | float | None = None
    source: str = "未知"
    has_hires: bool = False

    @field_validator("id", "url_id", "pic_id", "lyric_id", "name", "album", "source", mode="before")
    @classmethod
    def _coerce_text(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value)

    @field_validator("artist", mode="before")
    @classmethod
    def _coerce_artist(cls, value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if value is None:
            return "未知"
        return str(value)

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Song":
        return cls(
            id=data.get("id", ""),
            url_id=data.get("url_id", ""),
            pic_id=data.get("pic_id", ""),
            lyric_id=data.get("lyric_id", ""),
            name=data.get("name", "未知"),
            artist=get_artist_str(data),
            album=data.get("album", "未知"),
            duration=data.get("duration", 0),
            source=data.get("source", "未知"),
            has_hires=bool(data.get("has_hires", False)),
        )

    @property
    def display_name(self) -> str:
        return f"{self.name} [Hi-Res]" if self.has_hires else self.name

    @property
    def duration_text(self) -> str:
        return format_duration(self.duration)

    def to_legacy_dict(self) -> dict[str, str]:
        return {
            "name": self.display_name,
            "artist": self.artist,
            "album": self.album,
            "duration": self.duration_text,
            "source": self.source,
            "id": self.id,
            "url_id": self.url_id,
            "pic_id": self.pic_id,
            "lyric_id": self.lyric_id,
        }


class SearchOptions(BaseModel):
    keyword: str = Field(default=DEFAULT_KEYWORD, min_length=1)
    source: Source = Source(DEFAULT_SOURCE)
    search_type: SearchType = SearchType.SONG
    number: int = Field(default=DEFAULT_NUMBER, ge=1)
    output_format: OutputFormat = OutputFormat.TABLE


class DownloadOptions(BaseModel):
    source: Source = Source(DEFAULT_SOURCE)
    bitrate: Bitrate = Bitrate(DEFAULT_BITRATE)
    output_dir: Path
    group_name: str = ""
    download_lyric: bool = True
    download_cover: bool = True


class DownloadResult(BaseModel):
    song: Song
    status: DownloadStatus
    path: str = ""
    reason: str = ""
    warnings: list[str] = Field(default_factory=list)
    size_bytes: int = 0

    @property
    def ok(self) -> bool:
        return self.status in {DownloadStatus.SUCCESS, DownloadStatus.SKIP}


class AppSettings(BaseModel):
    source: Source = Source(DEFAULT_SOURCE)
    search_type: SearchType = SearchType.SONG
    bitrate: Bitrate = Bitrate(DEFAULT_BITRATE)
    number: int = Field(default=DEFAULT_NUMBER, ge=1)
    download_cover: bool = True
    download_lyric: bool = True
```

- [ ] **Step 5: Add error types**

Create `music_downloader/domain/errors.py`:

```python
"""Domain-specific exceptions with user-facing reasons."""

from __future__ import annotations


class MusicDownloaderError(Exception):
    """Base class for expected application errors."""


class BrowserStartupError(MusicDownloaderError):
    """Raised when Chrome or Playwright cannot start."""


class CloudflareError(MusicDownloaderError):
    """Raised when Cloudflare clearance cannot be obtained."""


class ApiRequestError(MusicDownloaderError):
    """Raised when the upstream music API cannot return usable data."""


class DownloadError(MusicDownloaderError):
    """Raised for a single-song download failure."""
```

- [ ] **Step 6: Run domain tests**

Run:

```powershell
python -m pytest tests/test_domain_models.py -q
```

Expected: `5 passed`.

- [ ] **Step 7: Commit**

```powershell
git add music_downloader/domain tests/test_domain_models.py
git commit -m "refactor: add typed domain models"
```

---

### Task 3: Shared File And Path Rules

**Files:**
- Create: `music_downloader/infrastructure/__init__.py`
- Create: `music_downloader/infrastructure/files.py`
- Modify: `music_downloader/utils.py`
- Create: `tests/test_file_rules.py`

- [ ] **Step 1: Write failing file rule tests**

Create `tests/test_file_rules.py`:

```python
from __future__ import annotations

from pathlib import Path

from music_downloader.domain.enums import Bitrate
from music_downloader.domain.models import Song
from music_downloader.infrastructure.files import (
    build_output_path,
    default_download_root,
    normalize_song_dict,
    output_exists,
    safe_filename,
)


def test_default_download_root_is_project_downloads() -> None:
    root = default_download_root()

    assert root.name == "downloads"
    assert (root.parent / "music_download.py").exists()


def test_build_output_path_matches_existing_filename_rule(tmp_path: Path) -> None:
    song = Song(id="42", name="Song:Name", artist="Artist", album="Album")

    path = build_output_path(tmp_path, song, Bitrate.MP3_320)

    assert path.name == "[42] Artist - Song_Name.mp3"


def test_flac_extension(tmp_path: Path) -> None:
    song = Song(id="42", name="Song", artist="Artist")

    path = build_output_path(tmp_path, song, Bitrate.FLAC)

    assert path.suffix == ".flac"


def test_output_exists_uses_final_path_only(tmp_path: Path) -> None:
    song = Song(id="42", name="Song", artist="Artist")
    path = build_output_path(tmp_path, song, Bitrate.MP3_320)
    path.write_bytes(b"already here")

    assert output_exists(path) is True


def test_normalize_song_dict_keeps_legacy_display_shape() -> None:
    data = normalize_song_dict({"id": "1", "name": "Song", "artist": ["A"], "duration": 61})

    assert data["name"] == "Song"
    assert data["artist"] == "A"
    assert data["duration"] == "1:01"


def test_safe_filename_handles_windows_reserved_name() -> None:
    assert safe_filename("CON.mp3") == "_CON.mp3"
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest tests/test_file_rules.py -q
```

Expected: FAIL because `music_downloader.infrastructure.files` does not exist yet.

- [ ] **Step 3: Add file infrastructure**

Create `music_downloader/infrastructure/__init__.py`:

```python
"""Infrastructure adapters for browser, files, metadata, and upstream APIs."""
```

Create `music_downloader/infrastructure/files.py`:

```python
"""Shared file naming and output path rules."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from music_downloader.domain.enums import Bitrate
from music_downloader.domain.models import Song
from music_downloader.utils import format_duration, get_artist_str

WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_download_root() -> Path:
    return project_root() / "downloads"


def safe_filename(name: str, max_length: int = 180) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]', "_", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    if not cleaned:
        cleaned = "download"
    stem, ext = os.path.splitext(cleaned)
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    max_stem_length = max_length - len(ext)
    if len(stem) > max_stem_length:
        stem = stem[:max_stem_length].rstrip(" .")
    return f"{stem}{ext}"


def output_extension(bitrate: Bitrate | str) -> str:
    value = bitrate.value if isinstance(bitrate, Bitrate) else str(bitrate)
    return ".flac" if value == Bitrate.FLAC.value else ".mp3"


def build_output_path(root: str | os.PathLike[str], song: Song, bitrate: Bitrate | str) -> Path:
    filename = safe_filename(
        f"[{song.id}] {song.artist} - {song.name}{output_extension(bitrate)}"
    )
    return Path(root) / filename


def output_exists(path: str | os.PathLike[str]) -> bool:
    return Path(path).exists()


def ensure_directory(path: str | os.PathLike[str]) -> Path:
    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    return target


def normalize_song_dict(song: dict[str, Any]) -> dict[str, str]:
    model = Song.from_api(song)
    return {
        "name": model.display_name,
        "artist": get_artist_str(song),
        "album": str(song.get("album", "未知")),
        "duration": format_duration(song.get("duration", 0)),
        "source": str(song.get("source", "未知")),
        "id": model.id,
        "url_id": model.url_id,
        "pic_id": model.pic_id,
        "lyric_id": model.lyric_id,
    }
```

- [ ] **Step 4: Convert utility wrappers**

In `music_downloader/utils.py`, keep existing public names and delegate filename and normalization logic:

```python
def sanitize_filename(name: str, max_length: int = 180) -> str:
    from music_downloader.infrastructure.files import safe_filename

    return safe_filename(name, max_length=max_length)


def normalize_song(song: dict[str, Any]) -> dict[str, str]:
    from music_downloader.infrastructure.files import normalize_song_dict

    return normalize_song_dict(song)
```

Keep `url_encode`, `format_duration`, `get_artist_str`, and `parse_selection` in `utils.py` unchanged.

- [ ] **Step 5: Run file rule tests**

Run:

```powershell
python -m pytest tests/test_file_rules.py -q
```

Expected: `6 passed`.

- [ ] **Step 6: Run existing import smoke**

Run:

```powershell
python -m pytest tests/test_imports.py tests/test_domain_models.py tests/test_file_rules.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```powershell
git add music_downloader/infrastructure music_downloader/utils.py tests/test_file_rules.py
git commit -m "refactor: centralize file naming rules"
```

---

### Task 4: Metadata Warning Semantics

**Files:**
- Create: `music_downloader/infrastructure/metadata.py`
- Modify: `music_downloader/downloader.py`
- Create: `tests/test_metadata_semantics.py`

- [ ] **Step 1: Write failing metadata semantics tests**

Create `tests/test_metadata_semantics.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from music_downloader.domain.enums import Bitrate, DownloadStatus
from music_downloader.domain.models import DownloadResult, Song
from music_downloader.infrastructure.metadata import MetadataWriter


def test_metadata_writer_returns_warning_when_embed_raises(tmp_path: Path) -> None:
    path = tmp_path / "song.mp3"
    path.write_bytes(b"audio")

    def broken_embed(**_: Any) -> None:
        raise RuntimeError("bad tag")

    writer = MetadataWriter(embed_func=broken_embed)
    warnings = writer.write(
        filepath=path,
        song=Song(id="1", name="Song"),
        index=1,
        total=1,
        cover_data=b"",
        cover_mime="image/jpeg",
        lyric_text="",
        bitrate=Bitrate.MP3_320,
    )

    assert warnings == ["写入元数据失败: bad tag"]
    assert path.exists()


def test_download_result_success_can_include_metadata_warning() -> None:
    result = DownloadResult(
        song=Song(id="1", name="Song"),
        status=DownloadStatus.SUCCESS,
        path="song.mp3",
        warnings=["写入元数据失败: bad tag"],
    )

    assert result.ok is True
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest tests/test_metadata_semantics.py -q
```

Expected: FAIL because `music_downloader.infrastructure.metadata` does not exist yet.

- [ ] **Step 3: Add metadata writer**

Create `music_downloader/infrastructure/metadata.py`:

```python
"""Warning-oriented metadata writing adapter."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from music_downloader.domain.enums import Bitrate
from music_downloader.domain.models import Song
from music_downloader.metadata import embed_metadata

EmbedFunc = Callable[..., None]


class MetadataWriter:
    def __init__(self, embed_func: EmbedFunc = embed_metadata):
        self._embed_func = embed_func

    def write(
        self,
        *,
        filepath: str | Path,
        song: Song,
        index: int,
        total: int,
        cover_data: bytes,
        cover_mime: str,
        lyric_text: str,
        bitrate: Bitrate | str,
    ) -> list[str]:
        try:
            self._embed_func(
                filepath=str(filepath),
                song=song.to_legacy_dict(),
                index=index,
                total=total,
                cover_data=cover_data,
                cover_mime=cover_mime,
                lyric_text=lyric_text,
                bitrate=bitrate.value if isinstance(bitrate, Bitrate) else str(bitrate),
            )
        except Exception as exc:  # noqa: BLE001 - metadata is best-effort
            return [f"写入元数据失败: {exc}"]
        return []
```

- [ ] **Step 4: Change legacy downloader metadata failure behavior**

In `music_downloader/downloader.py`, change `_attach_metadata` so metadata failure does not delete the downloaded file and does not return `False`. Replace the final block with:

```python
    embedded = _safe_embed_metadata(
        filepath=filepath,
        song=song,
        index=index,
        total=total,
        cover_data=cover_data,
        cover_mime=cover_mime,
        lyric_text=lyric_text,
        bitrate=bitrate,
    )
    if not embedded:
        console.print("  ⚠ 音频已下载，元数据写入失败已忽略", style="yellow")
    return True
```

- [ ] **Step 5: Run metadata tests**

Run:

```powershell
python -m pytest tests/test_metadata_semantics.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Run py_compile**

Run:

```powershell
python -m py_compile music_download.py
```

Expected: exits 0.

- [ ] **Step 7: Commit**

```powershell
git add music_downloader/infrastructure/metadata.py music_downloader/downloader.py tests/test_metadata_semantics.py
git commit -m "fix: treat metadata failures as download warnings"
```

---

### Task 5: GdStudio API Client And Search Service

**Files:**
- Create: `music_downloader/infrastructure/gdstudio.py`
- Create: `music_downloader/services/__init__.py`
- Create: `music_downloader/services/search.py`
- Modify: `music_downloader/api.py`
- Create: `tests/test_search_service.py`

- [ ] **Step 1: Write failing search service tests**

Create `tests/test_search_service.py`:

```python
from __future__ import annotations

from typing import Any

from music_downloader.domain.enums import SearchType, Source
from music_downloader.domain.models import SearchOptions
from music_downloader.services.search import SearchService


class FakeClient:
    def search(self, options: SearchOptions) -> list[dict[str, Any]]:
        assert options.search_type == SearchType.SONG
        return [
            {"id": "1", "name": "One", "artist": "A", "source": "netease"},
            {"id": "1", "name": "One Duplicate", "artist": "A", "source": "netease"},
            {"id": "2", "name": "Two", "artist": ["B"], "source": "netease"},
        ]


def test_search_service_deduplicates_by_id() -> None:
    service = SearchService(FakeClient())

    songs = service.search(SearchOptions(keyword="x", source=Source.NETEASE, number=10))

    assert [song.id for song in songs] == ["1", "2"]
    assert songs[1].artist == "B"
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest tests/test_search_service.py -q
```

Expected: FAIL because `music_downloader.services.search` does not exist yet.

- [ ] **Step 3: Add typed upstream client**

Create `music_downloader/infrastructure/gdstudio.py` by moving logic from current `music_downloader/api.py`. The public class must expose this surface:

```python
class GdStudioClient:
    def __init__(self, page: Any):
        self.page = page

    def search(self, options: SearchOptions) -> list[dict[str, Any]]:
        return search_with_pagination(
            self.page,
            options.keyword,
            options.source.value,
            options.search_type.value,
            options.number,
        )

    def get_play_url(self, song: Song, source: Source | str, bitrate: Bitrate | str) -> str:
        return get_play_url(self.page, song.to_legacy_dict(), _enum_value(source), _enum_value(bitrate))

    def get_lyric(self, song: Song, source: Source | str) -> str:
        return get_lyric(self.page, song.to_legacy_dict(), _enum_value(source))

    def get_pic_url(self, song: Song, source: Source | str) -> str:
        return get_pic_url(self.page, song.to_legacy_dict(), _enum_value(source))
```

Also move or re-export the existing functions `compute_signature`, `wait_for_cloudflare`, `refresh_cloudflare`, `fetch_api`, `fetch_with_cf_retry`, `search_with_pagination`, `get_play_url`, `get_lyric`, and `get_pic_url` so current callers keep working.

- [ ] **Step 4: Keep `api.py` as compatibility wrapper**

Replace `music_downloader/api.py` with imports from `infrastructure.gdstudio`:

```python
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
```

- [ ] **Step 5: Add search service**

Create `music_downloader/services/__init__.py`:

```python
"""Application services shared by CLI and GUI."""
```

Create `music_downloader/services/search.py`:

```python
"""Shared search workflow."""

from __future__ import annotations

from typing import Protocol

from music_downloader.domain.models import SearchOptions, Song


class SearchClient(Protocol):
    def search(self, options: SearchOptions) -> list[dict]:
        ...


class SearchService:
    def __init__(self, client: SearchClient):
        self._client = client

    def search(self, options: SearchOptions) -> list[Song]:
        raw_results = self._client.search(options)
        seen: set[str] = set()
        songs: list[Song] = []
        for item in raw_results:
            song = Song.from_api(item)
            if song.id and song.id in seen:
                continue
            if song.id:
                seen.add(song.id)
            songs.append(song)
        return songs[: options.number]
```

- [ ] **Step 6: Run search service tests**

Run:

```powershell
python -m pytest tests/test_search_service.py -q
```

Expected: `1 passed`.

- [ ] **Step 7: Run compatibility smoke**

Run:

```powershell
python -m py_compile music_download.py
python -m pytest tests/test_imports.py tests/test_search_service.py -q
```

Expected: all commands pass.

- [ ] **Step 8: Commit**

```powershell
git add music_downloader/infrastructure/gdstudio.py music_downloader/services music_downloader/api.py tests/test_search_service.py
git commit -m "refactor: add typed search service"
```

---

### Task 6: Download Service

**Files:**
- Create: `music_downloader/services/download.py`
- Modify: `music_downloader/downloader.py`
- Create: `tests/test_download_service.py`

- [ ] **Step 1: Write failing download service tests**

Create `tests/test_download_service.py`:

```python
from __future__ import annotations

from pathlib import Path

from music_downloader.domain.enums import Bitrate, DownloadStatus, Source
from music_downloader.domain.models import DownloadOptions, Song
from music_downloader.services.download import DownloadService


class FakeClient:
    def __init__(self, play_url: str = "http://example.test/audio.mp3"):
        self.play_url = play_url

    def get_play_url(self, song: Song, source: Source | str, bitrate: Bitrate | str) -> str:
        return self.play_url

    def get_lyric(self, song: Song, source: Source | str) -> str:
        return "lyric"

    def get_pic_url(self, song: Song, source: Source | str) -> str:
        return ""


class FakeFileDownloader:
    def download(self, url: str, path: Path) -> int:
        path.write_bytes(b"x" * 20000)
        return path.stat().st_size


class BrokenMetadata:
    def write(self, **kwargs: object) -> list[str]:
        return ["写入元数据失败: bad tag"]


def test_existing_file_is_skip(tmp_path: Path) -> None:
    song = Song(id="1", name="Song", artist="A")
    existing = tmp_path / "[1] A - Song.mp3"
    existing.write_bytes(b"exists")
    service = DownloadService(FakeClient(), FakeFileDownloader(), BrokenMetadata())

    result = service.download_one(
        song,
        DownloadOptions(output_dir=tmp_path, source=Source.NETEASE, bitrate=Bitrate.MP3_320),
        index=1,
        total=1,
    )

    assert result.status == DownloadStatus.SKIP
    assert result.path == str(existing)


def test_metadata_warning_still_success(tmp_path: Path) -> None:
    song = Song(id="1", name="Song", artist="A")
    service = DownloadService(FakeClient(), FakeFileDownloader(), BrokenMetadata())

    result = service.download_one(
        song,
        DownloadOptions(output_dir=tmp_path, source=Source.NETEASE, bitrate=Bitrate.MP3_320),
        index=1,
        total=1,
    )

    assert result.status == DownloadStatus.SUCCESS
    assert result.warnings == ["写入元数据失败: bad tag"]
    assert Path(result.path).exists()


def test_missing_play_url_fails_without_creating_file(tmp_path: Path) -> None:
    song = Song(id="1", name="Song", artist="A")
    service = DownloadService(FakeClient(play_url=""), FakeFileDownloader(), BrokenMetadata())

    result = service.download_one(
        song,
        DownloadOptions(output_dir=tmp_path, source=Source.NETEASE, bitrate=Bitrate.MP3_320),
        index=1,
        total=1,
    )

    assert result.status == DownloadStatus.FAIL
    assert result.reason == "未获取到播放链接"
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest tests/test_download_service.py -q
```

Expected: FAIL because `music_downloader.services.download` does not exist yet.

- [ ] **Step 3: Add download service**

Create `music_downloader/services/download.py`:

```python
"""Shared download workflow for CLI and GUI."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from music_downloader.domain.enums import Bitrate, DownloadStatus, Source
from music_downloader.domain.models import DownloadOptions, DownloadResult, Song
from music_downloader.infrastructure.files import build_output_path, ensure_directory, output_exists


class DownloadClient(Protocol):
    def get_play_url(self, song: Song, source: Source | str, bitrate: Bitrate | str) -> str:
        ...

    def get_lyric(self, song: Song, source: Source | str) -> str:
        ...

    def get_pic_url(self, song: Song, source: Source | str) -> str:
        ...


class FileDownloader(Protocol):
    def download(self, url: str, path: Path) -> int:
        ...


class MetadataWriterProtocol(Protocol):
    def write(self, **kwargs: object) -> list[str]:
        ...


class DownloadService:
    def __init__(
        self,
        client: DownloadClient,
        file_downloader: FileDownloader,
        metadata_writer: MetadataWriterProtocol,
    ):
        self._client = client
        self._file_downloader = file_downloader
        self._metadata_writer = metadata_writer

    def download_one(
        self,
        song: Song,
        options: DownloadOptions,
        *,
        index: int,
        total: int,
    ) -> DownloadResult:
        target_dir = ensure_directory(options.output_dir)
        target_path = build_output_path(target_dir, song, options.bitrate)
        if output_exists(target_path):
            return DownloadResult(song=song, status=DownloadStatus.SKIP, path=str(target_path))

        play_url = self._client.get_play_url(song, options.source, options.bitrate)
        if not play_url:
            return DownloadResult(song=song, status=DownloadStatus.FAIL, reason="未获取到播放链接")

        try:
            size_bytes = self._file_downloader.download(play_url, target_path)
        except Exception as exc:  # noqa: BLE001 - single-song failure
            return DownloadResult(song=song, status=DownloadStatus.FAIL, reason=str(exc))

        lyric_text = self._client.get_lyric(song, options.source) if options.download_lyric else ""
        cover_data = b""
        cover_mime = "image/jpeg"
        warnings = self._metadata_writer.write(
            filepath=target_path,
            song=song,
            index=index,
            total=total,
            cover_data=cover_data,
            cover_mime=cover_mime,
            lyric_text=lyric_text,
            bitrate=options.bitrate,
        )
        return DownloadResult(
            song=song,
            status=DownloadStatus.SUCCESS,
            path=str(target_path),
            warnings=warnings,
            size_bytes=size_bytes,
        )

    def download_many(self, songs: list[Song], options: DownloadOptions) -> list[DownloadResult]:
        total = len(songs)
        return [
            self.download_one(song, options, index=index + 1, total=total)
            for index, song in enumerate(songs)
        ]
```

- [ ] **Step 4: Preserve legacy `download_song` wrapper**

In `music_downloader/downloader.py`, keep `download_song` public behavior returning `"success"`, `"skip"`, or `"fail"` until CLI and GUI are migrated. Ensure the metadata failure branch from Task 4 remains:

```python
            ok = _attach_metadata(
                filepath=filepath,
                song=song,
                index=index,
                total=total,
                download_lyric=download_lyric,
                download_cover=download_cover,
                page=page,
                context=context,
                source=source,
                bitrate=bitrate,
            )
            return "success" if ok else "fail"
```

Because `_attach_metadata` now always returns `True` when the audio file exists, metadata warnings no longer produce `"fail"`.

- [ ] **Step 5: Run download service tests**

Run:

```powershell
python -m pytest tests/test_download_service.py tests/test_metadata_semantics.py -q
```

Expected: `5 passed`.

- [ ] **Step 6: Commit**

```powershell
git add music_downloader/services/download.py music_downloader/downloader.py tests/test_download_service.py
git commit -m "refactor: add shared download service"
```

---

### Task 7: Shared Browser Session And Environment Checks

**Files:**
- Create: `music_downloader/infrastructure/browser.py`
- Create: `music_downloader/infrastructure/environment.py`
- Modify: `music_downloader/env.py`
- Create: `tests/test_environment_checks.py`

- [ ] **Step 1: Write environment tests**

Create `tests/test_environment_checks.py`:

```python
from __future__ import annotations

from music_downloader.infrastructure.environment import EnvironmentCheck, run_environment_checks


def test_environment_checks_accept_fake_chrome_checker() -> None:
    def fake_chrome() -> EnvironmentCheck:
        return EnvironmentCheck("Google Chrome", True, "fake ok")

    checks = run_environment_checks(chrome_checker=fake_chrome)

    assert checks[-1].name == "Google Chrome"
    assert checks[-1].ok is True
```

- [ ] **Step 2: Add browser session**

Create `music_downloader/infrastructure/browser.py`:

```python
"""Shared Playwright browser session management."""

from __future__ import annotations

import contextlib
import os
import sys
from pathlib import Path
from typing import Any

from music_downloader.config import BASE_URL, PAGE_NAV_TIMEOUT_MS, USER_AGENT
from music_downloader.domain.errors import BrowserStartupError, CloudflareError
from music_downloader.infrastructure.gdstudio import wait_for_cloudflare


def runtime_root() -> Path:
    if "__compiled__" in globals():
        return Path(os.path.abspath(sys.argv[0])).parent
    return Path(__file__).resolve().parents[2]


def default_user_data_dir() -> Path:
    return runtime_root() / ".chrome-profile"


class BrowserSession:
    def __init__(self, *, user_data_dir: str | os.PathLike[str] | None = None, headless: bool = True):
        self.user_data_dir = Path(user_data_dir) if user_data_dir else default_user_data_dir()
        self.headless = headless
        self._playwright_cm: Any = None
        self._playwright: Any = None
        self.context: Any = None
        self.page: Any = None

    def __enter__(self) -> "BrowserSession":
        self.start()
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserStartupError("缺少运行依赖 playwright。请先运行: pip install -r requirements.txt") from exc

        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self._playwright_cm = sync_playwright()
        self._playwright = self._playwright_cm.start()
        try:
            self.context = self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.user_data_dir),
                channel="chrome",
                headless=self.headless,
                user_agent=USER_AGENT,
            )
        except Exception as exc:
            self.close()
            raise BrowserStartupError(f"无法启动系统 Google Chrome: {exc}") from exc
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        self.page.goto(BASE_URL, wait_until="networkidle", timeout=PAGE_NAV_TIMEOUT_MS)
        if not wait_for_cloudflare(self.page):
            raise CloudflareError("Cloudflare 验证未通过")

    def close(self) -> None:
        with contextlib.suppress(Exception):
            if self.context is not None:
                self.context.close()
        with contextlib.suppress(Exception):
            if self._playwright_cm is not None:
                self._playwright_cm.stop()
        self.context = None
        self.page = None
```

- [ ] **Step 3: Add environment infrastructure**

Create `music_downloader/infrastructure/environment.py` by moving current `music_downloader/env.py` code without changing behavior. Keep the public functions:

```python
EnvironmentCheck
check_python_version
check_module
check_chrome_launcher
run_environment_checks
render_environment_checks
check_environment
```

- [ ] **Step 4: Keep `env.py` as wrapper**

Replace `music_downloader/env.py` with:

```python
"""Compatibility wrapper for environment checks."""

from music_downloader.infrastructure.environment import (
    EnvironmentCheck,
    check_chrome_launcher,
    check_environment,
    check_module,
    check_python_version,
    render_environment_checks,
    run_environment_checks,
)

__all__ = [
    "EnvironmentCheck",
    "check_chrome_launcher",
    "check_environment",
    "check_module",
    "check_python_version",
    "render_environment_checks",
    "run_environment_checks",
]
```

- [ ] **Step 5: Run environment tests**

Run:

```powershell
python -m pytest tests/test_environment_checks.py -q
```

Expected: `1 passed`.

- [ ] **Step 6: Run py_compile**

Run:

```powershell
python -m py_compile music_download.py
```

Expected: exits 0.

- [ ] **Step 7: Commit**

```powershell
git add music_downloader/infrastructure/browser.py music_downloader/infrastructure/environment.py music_downloader/env.py tests/test_environment_checks.py
git commit -m "refactor: share browser and environment infrastructure"
```

---

### Task 8: Typer CLI Adapter

**Files:**
- Create: `music_downloader/adapters/__init__.py`
- Create: `music_downloader/adapters/cli/__init__.py`
- Create: `music_downloader/adapters/cli/legacy.py`
- Create: `music_downloader/adapters/cli/app.py`
- Create: `music_downloader/adapters/cli/interactive.py`
- Create: `music_downloader/adapters/cli/display.py`
- Modify: `music_downloader/cli.py`
- Modify: `music_downloader/display.py`
- Create: `tests/test_cli_adapter.py`

- [ ] **Step 1: Write CLI adapter tests**

Create `tests/test_cli_adapter.py`:

```python
from __future__ import annotations

from typer.testing import CliRunner

from music_downloader.adapters.cli.app import app
from music_downloader.adapters.cli.interactive import parse_interactive_command


def test_help_includes_existing_options() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "--keyword" in result.output
    assert "--search-only" in result.output
    assert "--gui" in result.output


def test_interactive_parser_keeps_existing_commands() -> None:
    assert parse_interactive_command("q").kind == "quit"
    assert parse_interactive_command("s netease").kind == "set_source"
    assert parse_interactive_command("n 10").kind == "set_number"
    assert parse_interactive_command("so").kind == "search_only"
```

- [ ] **Step 2: Run the failing tests**

Run:

```powershell
python -m pytest tests/test_cli_adapter.py -q
```

Expected: FAIL because `music_downloader.adapters.cli` does not exist yet.

- [ ] **Step 3: Add adapter package files**

Create `music_downloader/adapters/__init__.py`:

```python
"""User interface adapters."""
```

Create `music_downloader/adapters/cli/__init__.py`:

```python
"""Typer-based CLI adapter."""
```

Copy the current implementation of `music_downloader/cli.py` into `music_downloader/adapters/cli/legacy.py` and rename its public `main()` function to `legacy_main()`. Keep `parse_args`, `make_run_options`, `do_search_and_download`, `interactive_mode`, `import_playwright`, `fetch_player_version`, `_open_browser`, `_resolve_user_data_dir`, and `run_with_browser` unchanged in `legacy.py`.

Move current display functions from `music_downloader/display.py` to `music_downloader/adapters/cli/display.py` without behavior changes. Replace `music_downloader/display.py` with a compatibility wrapper importing `display_table`, `display_list`, and `display_results`.

- [ ] **Step 4: Move interactive parsing**

Create `music_downloader/adapters/cli/interactive.py` with current `InteractiveCommand`, `parse_interactive_command`, and `build_interactive_options` logic. Preserve these token constants:

```python
SET_SOURCE_PREFIX = "s "
SET_NUMBER_PREFIX = "n "
SEARCH_ONLY_TOKEN = "so"
QUIT_TOKEN = "q"
```

- [ ] **Step 5: Add Typer app shell**

Create `music_downloader/adapters/cli/app.py` with a Typer command that preserves existing options. The command body delegates to `music_downloader.adapters.cli.legacy` during this task:

```python
"""Typer CLI entrypoint."""

from __future__ import annotations

import sys
from typing import Annotated

import typer

from music_downloader.config import DEFAULT_BITRATE, DEFAULT_KEYWORD, DEFAULT_NUMBER, DEFAULT_SOURCE
from music_downloader.env import check_environment
from music_downloader.adapters.cli.legacy import parse_args, run_with_browser

app = typer.Typer(add_completion=False, help="music.gdstudio.org 音乐搜索与下载工具")


@app.callback(invoke_without_command=True)
def main_command(
    ctx: typer.Context,
    keyword: Annotated[str, typer.Option("-k", "--keyword", help="搜索关键词")] = DEFAULT_KEYWORD,
    source: Annotated[str, typer.Option("-s", "--source", help="音乐源")] = DEFAULT_SOURCE,
    number: Annotated[int, typer.Option("-n", "--number", min=1, help="获取结果总数")] = DEFAULT_NUMBER,
    search_type: Annotated[str, typer.Option("-t", "--type", help="搜索类型")] = "song",
    output_dir: Annotated[str, typer.Option("-o", "--output", help="下载目录")] = "",
    output_format: Annotated[str, typer.Option("-f", "--format", help="输出格式")] = "table",
    bitrate: Annotated[str, typer.Option("-b", "--bitrate", help="音质选择")] = DEFAULT_BITRATE,
    search_only: Annotated[bool, typer.Option("--search-only", help="只搜索不下载")] = False,
    select: Annotated[bool, typer.Option("--select", help="搜索后选择要下载的歌曲")] = False,
    no_lyric: Annotated[bool, typer.Option("--no-lyric", help="不下载歌词")] = False,
    no_cover: Annotated[bool, typer.Option("--no-cover", help="不嵌入封面")] = False,
    check_env: Annotated[bool, typer.Option("--check-env", help="检查本地依赖和 Google Chrome")] = False,
    interactive: Annotated[bool, typer.Option("-i", "--interactive", help="交互模式")] = False,
    gui: Annotated[bool, typer.Option("--gui", help="启动桌面图形界面")] = False,
    user_data_dir: Annotated[str | None, typer.Option("--user-data-dir", help="自定义 Chrome 用户数据目录")] = None,
) -> None:
    if check_env:
        raise typer.Exit(check_environment())
    if gui:
        from music_downloader.gui.app import run_gui

        run_gui()
        return
    argv = _to_legacy_argv(
        keyword,
        source,
        number,
        search_type,
        output_dir,
        output_format,
        bitrate,
        search_only,
        select,
        no_lyric,
        no_cover,
        interactive,
        user_data_dir,
    )
    code = run_with_browser(parse_args(argv))
    if code:
        raise typer.Exit(code)


def _to_legacy_argv(
    keyword: str,
    source: str,
    number: int,
    search_type: str,
    output_dir: str,
    output_format: str,
    bitrate: str,
    search_only: bool,
    select: bool,
    no_lyric: bool,
    no_cover: bool,
    interactive: bool,
    user_data_dir: str | None,
) -> list[str]:
    argv = [
        "--keyword",
        keyword,
        "--source",
        source,
        "--number",
        str(number),
        "--type",
        search_type,
        "--format",
        output_format,
        "--bitrate",
        bitrate,
    ]
    if output_dir:
        argv += ["--output", output_dir]
    if search_only:
        argv.append("--search-only")
    if select:
        argv.append("--select")
    if no_lyric:
        argv.append("--no-lyric")
    if no_cover:
        argv.append("--no-cover")
    if interactive:
        argv.append("--interactive")
    if user_data_dir:
        argv += ["--user-data-dir", user_data_dir]
    return argv


def main(argv: list[str] | None = None) -> None:
    if argv is None and len(sys.argv) <= 1:
        from music_downloader.gui.app import run_gui

        run_gui()
        return
    app(args=argv, standalone_mode=True)
```

- [ ] **Step 6: Make `music_downloader/cli.py` delegate to Typer**

Replace `music_downloader/cli.py` with this compatibility wrapper:

```python
"""Compatibility entrypoint for the Typer CLI adapter."""

from __future__ import annotations

from collections.abc import Sequence

from music_downloader.adapters.cli.app import app
from music_downloader.adapters.cli.app import main as _main
from music_downloader.adapters.cli.legacy import (
    build_interactive_options,
    do_search_and_download,
    fetch_player_version,
    import_playwright,
    interactive_mode,
    make_run_options,
    parse_args,
    parse_interactive_command,
    positive_int,
    run_with_browser,
)

__all__ = [
    "app",
    "build_interactive_options",
    "do_search_and_download",
    "fetch_player_version",
    "import_playwright",
    "interactive_mode",
    "make_run_options",
    "parse_args",
    "parse_interactive_command",
    "positive_int",
    "run_with_browser",
]


def main(argv: Sequence[str] | None = None) -> None:
    _main(list(argv) if argv is not None else None)
```

- [ ] **Step 7: Run CLI tests**

Run:

```powershell
python -m pytest tests/test_cli_adapter.py -q
python music_download.py -h
python -m music_downloader -h
```

Expected: tests pass and both help commands display Typer help with existing options.

- [ ] **Step 8: Commit**

```powershell
git add music_downloader/adapters music_downloader/cli.py music_downloader/display.py tests/test_cli_adapter.py
git commit -m "refactor: introduce typer cli adapter"
```

---

### Task 9: GUI Default Settings And Retry Failed Items

**Files:**
- Modify: `music_downloader/gui/settings.py`
- Modify: `music_downloader/gui/api.py`
- Modify: `music_downloader/gui/bridge.py`
- Modify: `music_downloader/gui/static/index.html`
- Modify: `music_downloader/gui/static/js/app.js`
- Modify: `music_downloader/gui/static/css/style.css`
- Create: `tests/test_gui_settings.py`

- [ ] **Step 1: Write GUI settings tests**

Create `tests/test_gui_settings.py`:

```python
from __future__ import annotations

from music_downloader.gui.settings import DEFAULT_CONFIG, load_config, save_config


def test_load_config_returns_defaults_each_time() -> None:
    config = load_config()

    assert config["source"] == DEFAULT_CONFIG["source"]
    assert config["number"] == DEFAULT_CONFIG["number"]
    assert config["output_dir"].endswith("downloads")


def test_save_config_does_not_persist_user_choices() -> None:
    save_config({"source": "spotify", "number": 5})

    config = load_config()

    assert config["source"] == DEFAULT_CONFIG["source"]
    assert config["number"] == DEFAULT_CONFIG["number"]
```

- [ ] **Step 2: Run failing GUI settings tests**

Run:

```powershell
python -m pytest tests/test_gui_settings.py -q
```

Expected: FAIL because current GUI settings persist values to the user home directory.

- [ ] **Step 3: Make GUI settings default-only**

Replace `music_downloader/gui/settings.py` with:

```python
"""Default-only GUI settings.

GUI choices are intentionally not persisted between runs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def _get_default_output_dir() -> str:
    if "__compiled__" in globals():
        base_dir = Path(os.path.dirname(os.path.abspath(sys.argv[0])))
    else:
        base_dir = Path(__file__).resolve().parent.parent.parent
    return str(base_dir / "downloads")


DEFAULT_CONFIG: dict[str, Any] = {
    "source": "netease",
    "search_type": "song",
    "bitrate": "320",
    "number": 20,
    "output_dir": _get_default_output_dir(),
    "download_cover": True,
    "download_lyric": True,
    "window_width": 960,
    "window_height": 680,
}


def load_config() -> dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    config["output_dir"] = _get_default_output_dir()
    return config


def save_config(config: dict[str, Any]) -> None:
    return None
```

- [ ] **Step 4: Update GUI API option validation**

In `music_downloader/gui/api.py`, keep `save_config()` returning `True` but understand it is a no-op. Update `search()` and `start_download()` to validate with Pydantic models:

```python
from pydantic import ValidationError
from music_downloader.domain.enums import Bitrate, SearchType, Source
from music_downloader.domain.models import SearchOptions
```

In `search()`:

```python
        try:
            options = SearchOptions(
                keyword=keyword.strip(),
                source=Source(source),
                search_type=SearchType(search_type),
                number=int(number),
            )
        except (ValidationError, ValueError):
            return []
        return self._bridge.search(
            options.keyword,
            options.source.value,
            options.search_type.value,
            options.number,
        )
```

In `start_download()`, validate `Source(source)` and `Bitrate(bitrate)` before delegating. If validation fails, return an empty task id.

- [ ] **Step 5: Update GUI bridge task status**

In `music_downloader/gui/bridge.py`, keep the dedicated Playwright thread. Change `_run_download()` so each result emits:

```python
{
    "type": "song_done",
    "task_id": task.task_id,
    "index": song_index,
    "result": result,
    "reason": reason,
    "path": filepath,
    "current": idx + 1,
    "total": total,
}
```

For legacy `download_song()` results, set `reason` to:

```python
reason = "" if result in ("success", "skip") else "下载失败，请查看日志"
```

Keep `_history` in memory only. Do not write a history file.

- [ ] **Step 6: Add retry failed items in GUI JS**

In `music_downloader/gui/static/js/app.js`, add state for failed indices:

```javascript
failedIndices: new Set(),
```

In the `song_done` event handler, update the set:

```javascript
if (d.result === 'fail') {
  state.failedIndices.add(d.index);
} else {
  state.failedIndices.delete(d.index);
}
updateRetryFailedUI();
```

Modify `music_downloader/gui/static/index.html` to add a button with id `retryFailedBtn` beside the download buttons, then add:

```javascript
function updateRetryFailedUI() {
  var btn = $('retryFailedBtn');
  if (!btn) return;
  var count = state.failedIndices.size;
  btn.disabled = count === 0;
  btn.textContent = count > 0 ? ('重试失败 (' + count + ')') : '重试失败';
}

async function retryFailed() {
  if (state.failedIndices.size === 0) return;
  state.selectedIndices = new Set(state.failedIndices);
  await doDownloadSelected();
}
```

Bind it:

```javascript
$('retryFailedBtn').addEventListener('click', retryFailed);
```

- [ ] **Step 7: Style retry failed button**

In `music_downloader/gui/static/css/style.css`, reuse the existing secondary button style for `#retryFailedBtn`. If there is no reusable class, add:

```css
#retryFailedBtn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
```

- [ ] **Step 8: Run GUI settings tests**

Run:

```powershell
python -m pytest tests/test_gui_settings.py -q
python -m py_compile music_download.py
```

Expected: tests pass and py_compile exits 0.

- [ ] **Step 9: Commit**

```powershell
git add music_downloader/gui tests/test_gui_settings.py
git commit -m "feat(gui): use default settings and retry failed downloads"
```

---

### Task 10: Complete Service Migration For CLI And GUI

**Files:**
- Modify: `music_downloader/cli.py`
- Modify: `music_downloader/gui/bridge.py`
- Modify: `music_downloader/services/download.py`
- Modify: `music_downloader/infrastructure/gdstudio.py`
- Modify: `music_downloader/infrastructure/files.py`
- Create: `tests/test_service_integration.py`

- [ ] **Step 1: Add service integration tests**

Create `tests/test_service_integration.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from music_downloader.domain.enums import Bitrate, DownloadStatus, Source
from music_downloader.domain.models import DownloadOptions, SearchOptions, Song
from music_downloader.services.download import DownloadService
from music_downloader.services.search import SearchService


class FakeClient:
    def search(self, options: SearchOptions) -> list[dict[str, Any]]:
        return [{"id": "1", "name": options.keyword, "artist": "A", "source": options.source.value}]

    def get_play_url(self, song: Song, source: Source | str, bitrate: Bitrate | str) -> str:
        return "http://example.test/audio.mp3"

    def get_lyric(self, song: Song, source: Source | str) -> str:
        return ""

    def get_pic_url(self, song: Song, source: Source | str) -> str:
        return ""


class FakeFileDownloader:
    def download(self, url: str, path: Path) -> int:
        path.write_bytes(b"x" * 20000)
        return path.stat().st_size


class NoopMetadata:
    def write(self, **kwargs: object) -> list[str]:
        return []


def test_search_then_download_shared_workflow(tmp_path: Path) -> None:
    client = FakeClient()
    songs = SearchService(client).search(SearchOptions(keyword="Song"))
    result = DownloadService(client, FakeFileDownloader(), NoopMetadata()).download_one(
        songs[0],
        DownloadOptions(output_dir=tmp_path, source=Source.NETEASE, bitrate=Bitrate.MP3_320),
        index=1,
        total=1,
    )

    assert result.status == DownloadStatus.SUCCESS
    assert Path(result.path).exists()
```

- [ ] **Step 2: Run service integration tests**

Run:

```powershell
python -m pytest tests/test_service_integration.py -q
```

Expected: test passes if previous service tasks were completed.

- [ ] **Step 3: Replace CLI orchestration with services**

In `music_downloader/cli.py`, update `do_search_and_download()` to:

1. Build `SearchOptions`.
2. Instantiate `GdStudioClient(page)`.
3. Call `SearchService(client).search(options)`.
4. Convert songs to legacy dicts only for display.
5. Build `DownloadOptions`.
6. Use shared file path functions for target directory.
7. Call `download_song()` legacy wrapper or `DownloadService` until both paths produce the same status counters.

The counters must be computed from `DownloadStatus`:

```python
if result.status == DownloadStatus.SUCCESS:
    success += 1
elif result.status == DownloadStatus.SKIP:
    skip += 1
else:
    fail += 1
```

- [ ] **Step 4: Replace GUI search with SearchService**

In `music_downloader/gui/bridge.py`, replace direct `search_with_pagination()` usage with:

```python
client = GdStudioClient(self._session.page)
results = SearchService(client).search(
    SearchOptions(keyword=keyword, source=Source(source), search_type=SearchType(search_type), number=number)
)
return [song.to_legacy_dict() for song in results]
```

- [ ] **Step 5: Keep cancellation behavior**

In GUI batch download, check `task.cancel_event.is_set()` before each song. If set, emit one complete event with current counts and do not mark pending songs as failed.

- [ ] **Step 6: Run full unit suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 7: Run CLI smoke checks**

Run:

```powershell
python music_download.py -h
python -m music_downloader -h
python music_download.py --check-env
```

Expected: help commands show options; `--check-env` runs environment checks and exits 0 if local dependencies and Chrome are available, or exits 1 with a clear table if something is missing.

- [ ] **Step 8: Commit**

```powershell
git add music_downloader/cli.py music_downloader/gui/bridge.py music_downloader/services music_downloader/infrastructure tests/test_service_integration.py
git commit -m "refactor: route cli and gui through shared services"
```

---

### Task 11: Documentation And Build Packaging

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `scripts/build_exe.ps1`
- Modify: `requirements.txt`
- Modify: `requirements-dev.txt`
- Modify: `pyproject.toml`
- Modify: `requirements-build.txt`

- [ ] **Step 1: Update README structure and dependencies**

Update README sections:

- Add GUI usage examples:

```bash
python music_download.py --gui
python music_download.py
```

Explain that no-argument source runs the GUI, and CLI usage requires options such as `-k`, `--check-env`, or `-i`.

- Add dependencies:

```text
typer>=0.12
pydantic>=2.7
pytest>=8.2 for development
```

- Update file structure to include `domain/`, `services/`, `infrastructure/`, and `adapters/`.

- State that metadata failures do not delete downloaded audio files.

- State that GUI settings reset to defaults each launch.

- Remove `rich-argparse` from `requirements.txt`, `requirements-dev.txt`, and `pyproject.toml` when `rg "rich_argparse|rich-argparse" .` returns no runtime imports outside historical docs.

- [ ] **Step 2: Update AGENTS structure notes**

Update `AGENTS.md` project structure and common modification sections:

- New domain models live in `music_downloader/domain/`.
- Search and download orchestration live in `music_downloader/services/`.
- Playwright and upstream API logic live in `music_downloader/infrastructure/`.
- CLI adapter lives in `music_downloader/adapters/cli/`.
- GUI remains pywebview static frontend.
- Metadata failure is warning-only; do not reintroduce deletion of successfully downloaded audio.

- [ ] **Step 3: Ensure build script includes GUI static resources after move**

If GUI static resources remain under `music_downloader/gui/static`, keep:

```powershell
"--include-data-dir=music_downloader/gui/static=music_downloader/gui/static"
```

If resources move to `music_downloader/adapters/gui/static`, change it to:

```powershell
"--include-data-dir=music_downloader/adapters/gui/static=music_downloader/adapters/gui/static"
```

Keep `music_download.py` as the single Nuitka entrypoint and `--output-filename=music_download.exe`.

- [ ] **Step 4: Run documentation-sensitive checks**

Run:

```powershell
python -m py_compile music_download.py
python music_download.py -h
```

Expected: py_compile exits 0 and help output matches README examples.

- [ ] **Step 5: Commit**

```powershell
git add README.md AGENTS.md scripts/build_exe.ps1 pyproject.toml requirements-build.txt
git commit -m "docs: update refactored architecture and build notes"
```

---

### Task 12: Final Verification

**Files:**
- No source edits unless verification reveals a concrete defect.

- [ ] **Step 1: Run unit tests**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Run Ruff**

Run:

```powershell
python -m ruff check .
python -m ruff format --check .
```

Expected: both commands exit 0.

- [ ] **Step 3: Run mypy**

Run:

```powershell
python -m mypy music_downloader
```

Expected: exits 0.

- [ ] **Step 4: Run py_compile**

Run:

```powershell
python -m py_compile music_download.py
```

Expected: exits 0.

- [ ] **Step 5: Verify CLI environment command**

Run:

```powershell
python music_download.py --check-env
```

Expected: prints the environment table. Exit code is 0 when dependencies and Chrome are present; exit code 1 is acceptable only if the table clearly identifies the missing local dependency.

- [ ] **Step 6: Verify no-argument GUI entrypoint manually**

Run:

```powershell
python music_download.py
```

Expected: pywebview GUI opens. Close it after confirming the default source, type, count, bitrate, lyric, cover, and output directory values are default values.

- [ ] **Step 7: Verify onefile packaging command**

Run:

```powershell
.\scripts\build_exe.ps1 -SkipInstall
```

Expected: `dist/music_download.exe` is produced.

- [ ] **Step 8: Verify generated exe supports CLI and GUI**

Run:

```powershell
.\dist\music_download.exe --check-env
.\dist\music_download.exe -h
.\dist\music_download.exe --gui
```

Expected:

- `--check-env` runs environment checks.
- `-h` displays CLI help.
- `--gui` opens the GUI and finds its `index.html`.

- [ ] **Step 9: Commit verification fixes if any**

If verification reveals source or doc fixes, commit only those fixes:

```powershell
git add <changed-files>
git commit -m "fix: address final refactor verification issues"
```

If verification passes without changes, do not create an empty commit.

---

## Self-Review

- Spec coverage: the plan covers the shared core, Pydantic models, Typer CLI, pytest, GUI default settings, retry failed downloads, metadata warning semantics, and single exe GUI/CLI packaging.
- Unfinished-marker scan: the plan gives concrete files, code snippets, commands, and expected outcomes.
- Type consistency: `Song`, `SearchOptions`, `DownloadOptions`, `DownloadResult`, `Source`, `SearchType`, `Bitrate`, and `DownloadStatus` are introduced before later tasks use them.
- Scope control: FastAPI and front-end build tools are excluded; GUI remains pywebview and static assets.
