# Search Result Duration Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Correctly display search-result durations in GUI and CLI by reading the current GD Studio `extra_data` response structure.

**Architecture:** Keep the upstream response unchanged in `GdStudioClient` and adapt it at the existing `Song.from_api()` domain boundary. Read `duration` and optional `has_hires` strictly from `extra_data`, with no fallback to legacy top-level fields; existing serialization and renderers remain unchanged.

**Tech Stack:** Python 3.11+, Pydantic 2.7+, pytest 8.2+, Ruff 0.5+, mypy 1.10+

## Global Constraints

- Use Python 3.11+ syntax and PEP 604 unions.
- Do not access the real music site from unit tests.
- Do not read or fall back to top-level `duration` or `has_hires`.
- Preserve the existing `--:--` unknown-duration behavior.
- Do not modify Svelte sources or generated GUI static assets for this fix.
- Preserve unrelated user changes in the dirty worktree.

---

### Task 1: Parse current search-result metadata at the domain boundary

**Files:**
- Modify: `tests/test_domain_models.py`
- Modify: `tests/test_file_rules.py`
- Modify: `music_downloader/domain/models.py:65-80`
- Modify: `music_downloader/infrastructure/files.py:54-68`

**Interfaces:**
- Consumes: `Song.from_api(data: dict[str, Any]) -> Song` and the upstream `extra_data` mapping.
- Produces: `Song.duration`, `Song.has_hires`, `Song.duration_text`, and `Song.display_name` populated from the current nested response structure.
- Preserves: the already formatted top-level duration in the project's internal `Song.to_result_dict()` display dictionary.

- [ ] **Step 1: Replace the legacy-shaped model test with current response shapes**

Update `tests/test_domain_models.py` so the main API-shape test is parameterized across the three verified sources and add a strict no-fallback regression test:

```python
@pytest.mark.parametrize(
    ("source", "duration", "has_hires", "expected_duration", "expected_name"),
    [
        pytest.param("netease", 131, True, "2:11", "Track [Hi-Res]", id="netease"),
        pytest.param("spotify", 231, False, "3:51", "Track", id="spotify"),
        pytest.param("kuwo", 324, False, "5:24", "Track", id="kuwo"),
    ],
)
def test_song_accepts_current_api_dict(
    source: str,
    duration: int,
    has_hires: bool,
    expected_duration: str,
    expected_name: str,
) -> None:
    extra_data: dict[str, object] = {"duration": duration}
    if has_hires:
        extra_data["has_hires"] = True
    song = Song.from_api(
        {
            "id": 123,
            "url_id": "u-1",
            "pic_id": "p-1",
            "lyric_id": "l-1",
            "name": "Track",
            "artist": ["A", "B"],
            "album": "Album",
            "source": source,
            "extra_data": extra_data,
        }
    )

    assert song.id == "123"
    assert song.artist == "A, B"
    assert song.duration_text == expected_duration
    assert song.display_name == expected_name


def test_song_does_not_fall_back_to_legacy_top_level_metadata() -> None:
    song = Song.from_api(
        {
            "id": "1",
            "name": "Track",
            "duration": 125,
            "has_hires": True,
        }
    )

    assert song.duration_text == "--:--"
    assert song.display_name == "Track"
```

- [ ] **Step 2: Run the regression tests and verify RED**

Run:

```powershell
python -m pytest tests/test_domain_models.py -q
```

Expected: the three `test_song_accepts_current_api_dict` cases fail because nested durations become `--:--`, and the strict no-fallback test fails because top-level metadata is still accepted.

- [ ] **Step 3: Implement strict nested metadata parsing**

In `Song.from_api()`, normalize only `extra_data` and use it as the sole source for both fields:

```python
    @classmethod
    def from_api(cls, data: dict[str, Any]) -> Song:
        extra_data = data.get("extra_data")
        if not isinstance(extra_data, dict):
            extra_data = {}
        return cls(
            id=data.get("id", ""),
            url_id=data.get("url_id", ""),
            pic_id=data.get("pic_id", ""),
            lyric_id=data.get("lyric_id", ""),
            name=data.get("name", "未知"),
            artist=get_artist_str(data),
            album=data.get("album", "未知"),
            duration=extra_data.get("duration", 0),
            source=data.get("source", "未知"),
            has_hires=bool(extra_data.get("has_hires", False)),
        )
```

- [ ] **Step 4: Decouple internal display normalization from upstream parsing**

Update `normalize_song_dict()` so it no longer sends the internal `Song.to_result_dict()` shape back through `Song.from_api()`:

```python
def normalize_song_dict(song: dict[str, Any]) -> dict[str, str]:
    model = Song(
        id=song.get("id", ""),
        url_id=song.get("url_id", ""),
        pic_id=song.get("pic_id", ""),
        lyric_id=song.get("lyric_id", ""),
        name=song.get("name", "未知"),
        artist=get_artist_str(song),
    )
    duration = song.get("duration", "--:--")
    duration_text = str(duration).strip() if duration is not None else "--:--"
    return {
        "name": model.display_name,
        "artist": get_artist_str(song),
        "album": str(song.get("album", "未知")),
        "duration": duration_text or "--:--",
        "source": str(song.get("source", "未知")),
        "id": model.id,
        "url_id": model.url_id,
        "pic_id": model.pic_id,
        "lyric_id": model.lyric_id,
    }
```

Update `test_normalize_song_dict_keeps_display_shape()` to construct a `Song` from nested upstream metadata and pass `song.to_result_dict()` to `normalize_song_dict()`. Before this implementation, the test must fail because `"1:01"` is lost; afterward it must pass.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_domain_models.py tests/test_search_service.py tests/test_file_rules.py -q
```

Expected: all selected tests pass with zero failures.

- [ ] **Step 6: Run static checks for the changed Python files**

Run:

```powershell
python -m ruff check music_downloader/domain/models.py music_downloader/infrastructure/files.py tests/test_domain_models.py tests/test_file_rules.py
python -m ruff format --check music_downloader/domain/models.py music_downloader/infrastructure/files.py tests/test_domain_models.py tests/test_file_rules.py
python -m mypy music_downloader
```

Expected: all commands exit with status 0.

- [ ] **Step 7: Verify the complete Python test suite**

Run:

```powershell
python -m pytest -q
```

Expected: the full test suite passes with zero failures.

- [ ] **Step 8: Verify three live source results without downloading**

Use the existing Playwright search path in an isolated temporary Chrome profile to fetch one result each from `netease`, `spotify`, and `kuwo`, pass each raw result through `Song.from_api()`, and print `source`, raw `extra_data.duration`, and serialized `duration`.

Expected: every source has a positive nested raw duration and a non-`--:--` serialized duration.

- [ ] **Step 9: Review and commit only the scoped files**

Run:

```powershell
git diff --check -- music_downloader/domain/models.py music_downloader/infrastructure/files.py tests/test_domain_models.py tests/test_file_rules.py docs/superpowers/plans/2026-07-12-search-result-duration-fix.md
git diff -- music_downloader/domain/models.py music_downloader/infrastructure/files.py tests/test_domain_models.py tests/test_file_rules.py
git add music_downloader/domain/models.py music_downloader/infrastructure/files.py tests/test_domain_models.py tests/test_file_rules.py docs/superpowers/plans/2026-07-12-search-result-duration-fix.md
git diff --cached --name-only
git commit -m "fix: parse nested search result metadata"
```

Expected: the staged file list contains exactly the two production files, two test files, and this implementation plan, and the commit succeeds without including unrelated worktree changes.
