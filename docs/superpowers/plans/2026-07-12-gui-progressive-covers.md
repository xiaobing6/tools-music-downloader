# GUI Progressive Search Covers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep GUI searches fast while resolving and displaying each result cover progressively in the background.

**Architecture:** `MusicBridge.search()` returns serialized songs immediately, then a generation-scoped daemon worker resolves each `pic_id` through the existing signed `get_pic_url()` path on the dedicated Playwright thread. Successful resolutions flow through `MusicApi` as `py-cover` events, and Svelte immutably updates the matching current song so the existing result row swaps its placeholder for the image.

**Tech Stack:** Python 3.11+, Playwright sync API, pywebview 5+, Svelte 5, TypeScript, pytest 8.2+, Node test runner, Ruff, mypy, Vite

## Global Constraints

- Keep all Playwright operations on `_PlaywrightThread`.
- Resolve covers sequentially; do not issue concurrent batches to the upstream site.
- Do not block the GUI search response on cover resolution.
- A failed cover must leave the placeholder visible and must not fail the search or remaining covers.
- A new search or shutdown must invalidate the previous cover worker.
- Do not change CLI search behavior or result-row visual dimensions.
- Refresh `music_downloader/gui/static/` through the frontend build; never edit generated assets directly.
- Preserve unrelated dirty-worktree changes and do not create a Git commit.

---

### Task 1: Emit progressive cover events from the GUI backend

**Files:**
- Modify: `music_downloader/gui/bridge.py:18-275,462-467`
- Modify: `music_downloader/gui/api.py:32-70`
- Modify: `tests/test_gui_bridge.py`
- Create: `tests/test_gui_covers.py`

**Interfaces:**
- Consumes: `GdStudioClient.get_pic_url(song: Song, source: Source | str) -> str`.
- Produces: `CoverCallback = Callable[[dict[str, str]], None]` events with `id`, `source`, and `cover`.
- Produces: browser event `py-cover` with the same detail object.

- [ ] **Step 1: Add failing bridge tests for immediate return, failure isolation, and stale-task cancellation**

Append tests to `tests/test_gui_bridge.py` using the existing `_InlineSession` helper. Patch `GdStudioClient` with fakes and assert the wished-for private worker contract:

```python
from music_downloader.domain.models import Song


def test_gui_search_returns_before_progressive_cover_resolution(monkeypatch) -> None:
    captured: list[tuple[list[Song], str, int]] = []

    class FakeClient:
        def __init__(self, _page: object) -> None:
            pass

        def search(self, _options: object) -> list[dict[str, object]]:
            return [
                {
                    "id": "1",
                    "name": "Song",
                    "artist": ["Artist"],
                    "source": "netease",
                    "pic_id": "pic-1",
                    "extra_data": {"duration": 61},
                }
            ]

    bridge = MusicBridge(on_cover=lambda _detail: None)
    bridge._session = _InlineSession()  # type: ignore[assignment]
    monkeypatch.setattr(bridge, "ensure_browser", lambda: True)
    monkeypatch.setattr(bridge_module, "GdStudioClient", FakeClient)
    monkeypatch.setattr(
        bridge,
        "_start_cover_resolution",
        lambda songs, source, generation: captured.append((songs, source, generation)),
    )

    results = bridge.search("Song", "netease", "song", 1)

    assert "cover" not in results[0]
    assert captured[0][0][0].pic_id == "pic-1"
    assert captured[0][1] == "netease"


def test_cover_resolution_continues_after_one_song_fails(monkeypatch) -> None:
    events: list[dict[str, str]] = []

    class FakeClient:
        def __init__(self, _page: object) -> None:
            pass

        def get_pic_url(self, song: Song, _source: str) -> str:
            if song.id == "2":
                raise RuntimeError("cover failed")
            return f"https://covers.example/{song.id}.jpg"

    bridge = MusicBridge(on_cover=events.append)
    bridge._session = _InlineSession()  # type: ignore[assignment]
    bridge._cover_generation = 1
    monkeypatch.setattr(bridge_module, "GdStudioClient", FakeClient)

    bridge._resolve_covers(
        [Song(id="1", pic_id="p1"), Song(id="2", pic_id="p2"), Song(id="3", pic_id="p3")],
        "netease",
        1,
    )

    assert [event["id"] for event in events] == ["1", "3"]


def test_cover_resolution_stops_when_generation_changes(monkeypatch) -> None:
    events: list[dict[str, str]] = []
    requested: list[str] = []

    class FakeClient:
        def __init__(self, _page: object) -> None:
            pass

        def get_pic_url(self, song: Song, _source: str) -> str:
            requested.append(song.id)
            return f"https://covers.example/{song.id}.jpg"

    bridge = MusicBridge()
    bridge._session = _InlineSession()  # type: ignore[assignment]
    bridge._cover_generation = 1

    def handle_cover(detail: dict[str, str]) -> None:
        events.append(detail)
        bridge._cover_generation = 2

    bridge._on_cover = handle_cover
    monkeypatch.setattr(bridge_module, "GdStudioClient", FakeClient)

    bridge._resolve_covers(
        [Song(id="1", pic_id="p1"), Song(id="2", pic_id="p2")],
        "netease",
        1,
    )

    assert requested == ["1"]
    assert [event["id"] for event in events] == ["1"]
```

- [ ] **Step 2: Run bridge tests and verify RED**

Run: `python -m pytest tests/test_gui_bridge.py -q`

Expected: failures report that `MusicBridge` has no `on_cover`, `_cover_generation`, `_resolve_covers`, or `_start_cover_resolution` support.

- [ ] **Step 3: Implement generation-scoped progressive resolution in `MusicBridge`**

Import `Song`, define `CoverCallback`, store the callback and generation, and add these methods:

```python
CoverCallback = Callable[[dict[str, str]], None]


def _emit_cover(self, data: dict[str, str]) -> None:
    if self._on_cover:
        self._on_cover(data)


def _resolve_covers(self, songs: list[Song], source: str, generation: int) -> None:
    client = GdStudioClient(self._session.page)
    for song in songs:
        if generation != self._cover_generation:
            return
        if not song.pic_id:
            continue
        try:
            cover = self._session.submit(
                lambda current=song: client.get_pic_url(current, source),
                timeout=60.0,
            )
        except Exception:  # noqa: BLE001
            if generation != self._cover_generation:
                return
            continue
        if generation != self._cover_generation:
            return
        if cover:
            self._emit_cover({"id": song.id, "source": source, "cover": str(cover)})


def _start_cover_resolution(
    self,
    songs: list[Song],
    source: str,
    generation: int,
) -> None:
    if not songs or self._on_cover is None:
        return
    thread = threading.Thread(
        target=self._resolve_covers,
        args=(songs, source, generation),
        daemon=True,
    )
    thread.start()
```

Change `search()` to increment `_cover_generation` before browser initialization, submit a callable returning `list[Song]`, serialize after the submit completes, then call `_start_cover_resolution(songs, source, generation)` after logging the result count. Increment `_cover_generation` at the beginning of `shutdown()` before stopping tasks and the browser session.

- [ ] **Step 4: Add a failing API forwarding test**

Create `tests/test_gui_covers.py`:

```python
from music_downloader.gui.api import MusicApi


class FakeWindow:
    def __init__(self) -> None:
        self.scripts: list[str] = []

    def evaluate_js(self, script: str) -> None:
        self.scripts.append(script)


def test_gui_api_emits_cover_event() -> None:
    api = MusicApi()
    window = FakeWindow()
    api.set_window(window)

    api._handle_cover(
        {"id": "1", "source": "netease", "cover": "https://covers.example/1.jpg"}
    )

    assert "py-cover" in window.scripts[-1]
    assert '"id": "1"' in window.scripts[-1]
    assert '"cover": "https://covers.example/1.jpg"' in window.scripts[-1]
```

- [ ] **Step 5: Run API test and verify RED**

Run: `python -m pytest tests/test_gui_covers.py -q`

Expected: FAIL because `MusicApi` has no `_handle_cover` method and does not pass `on_cover` into `MusicBridge`.

- [ ] **Step 6: Forward bridge cover callbacks through `MusicApi`**

Pass `on_cover=self._handle_cover` to `MusicBridge` and add:

```python
def _handle_cover(self, data: dict[str, str]) -> None:
    self._emit("cover", data)
```

- [ ] **Step 7: Verify backend GREEN**

Run: `python -m pytest tests/test_gui_bridge.py tests/test_gui_covers.py -q`

Expected: all selected tests pass.

---

### Task 2: Apply cover events to the current Svelte result list

**Files:**
- Modify: `music_downloader/gui/frontend/src/lib/types.ts`
- Modify: `music_downloader/gui/frontend/src/lib/api.ts`
- Modify: `music_downloader/gui/frontend/src/App.svelte`
- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs`

**Interfaces:**
- Consumes: window event `py-cover`.
- Produces: `CoverDetail { id: string; source: string; cover: string }` and `onPythonCover(handler) -> cleanup`.
- Updates: matching `Song.cover` in the reactive `songs` array.

- [ ] **Step 1: Add a failing frontend source-contract test**

Append to `workbench.test.mjs`:

```javascript
test("search covers are applied progressively and listeners are cleaned up", async () => {
  const app = await source("App.svelte");
  const api = await source("lib/api.ts");
  const types = await source("lib/types.ts");

  assert.match(types, /interface CoverDetail/);
  assert.match(api, /onPythonCover/);
  assert.match(api, /py-cover/);
  assert.match(app, /onPythonCover\(handleCover\)/);
  assert.match(app, /songs = songs\.map/);
  assert.match(app, /removeCoverListener\(\)/);
});
```

- [ ] **Step 2: Run the frontend contract test and verify RED**

Run: `node --test music_downloader/gui/frontend/tests/workbench.test.mjs`

Expected: the progressive-cover test fails because the type, listener, handler, and cleanup are absent.

- [ ] **Step 3: Add the typed `py-cover` listener**

Add to `types.ts`:

```typescript
export interface CoverDetail {
  id: string;
  source: string;
  cover: string;
}
```

Import `CoverDetail` in `api.ts` and add:

```typescript
export function onPythonCover(handler: (detail: CoverDetail) => void): () => void {
  const listener = (event: Event) => {
    handler((event as CustomEvent<CoverDetail>).detail);
  };
  window.addEventListener("py-cover", listener);
  return () => window.removeEventListener("py-cover", listener);
}
```

- [ ] **Step 4: Update `App.svelte` immutably and clean up the listener**

Import `onPythonCover` and `CoverDetail`, then add:

```typescript
function handleCover(detail: CoverDetail) {
  songs = songs.map((song) =>
    String(song.id ?? "") === detail.id && String(song.source ?? "") === detail.source
      ? { ...song, cover: detail.cover }
      : song
  );
}
```

In `onMount()`, create `const removeCoverListener = onPythonCover(handleCover);` and call `removeCoverListener()` in the returned cleanup function.

- [ ] **Step 5: Verify frontend GREEN and compile checks**

Run:

```powershell
node --test music_downloader/gui/frontend/tests/startup.test.mjs music_downloader/gui/frontend/tests/workbench.test.mjs
npm.cmd --prefix music_downloader/gui/frontend run check
```

Expected: Node tests and Svelte check pass.

---

### Task 3: Document, build, and verify the complete behavior

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `tests/test_gui_documentation.py`
- Regenerate: `music_downloader/gui/static/**`

**Interfaces:**
- Documents: search returns before covers and covers load progressively with placeholder fallback.
- Delivers: built Svelte assets containing the `py-cover` listener.

- [ ] **Step 1: Add a failing documentation contract test**

In `test_gui_docs_cover_visual_polish_contract()`, add:

```python
assert "封面逐张加载" in readme
assert "封面逐张加载" in agents
```

- [ ] **Step 2: Run the documentation test and verify RED**

Run: `python -m pytest tests/test_gui_documentation.py -q`

Expected: FAIL because neither user nor contributor documentation mentions progressive cover loading.

- [ ] **Step 3: Update user and contributor documentation**

Extend the compact-result paragraph in both files with the exact phrase `封面逐张加载` and state that failed cover resolution keeps the default icon without blocking search.

- [ ] **Step 4: Run focused checks and rebuild generated static assets**

Run:

```powershell
python -m pytest tests/test_gui_bridge.py tests/test_gui_covers.py tests/test_gui_documentation.py -q
node --test music_downloader/gui/frontend/tests/startup.test.mjs music_downloader/gui/frontend/tests/workbench.test.mjs
npm.cmd --prefix music_downloader/gui/frontend run check
npm.cmd --prefix music_downloader/gui/frontend run build
```

Expected: all commands exit 0 and `gui/static/index.html` references the newly generated JavaScript asset.

- [ ] **Step 5: Run complete static and automated verification**

Run:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m pytest -q
```

Expected: all checks pass with zero failures.

- [ ] **Step 6: Verify live progressive behavior without downloading**

Use an isolated temporary Chrome profile and a `MusicBridge` with an `on_cover` callback. Search one result each from `netease`, `spotify`, and `kuwo`; record the search return time and wait for one cover event per source.

Expected: each search result returns without a `cover` key before its event, every event contains an HTTP URL, and no audio download is attempted.

- [ ] **Step 7: Review scope without committing**

Run:

```powershell
git diff --check
git status --short
git diff -- music_downloader/gui/bridge.py music_downloader/gui/api.py music_downloader/gui/frontend/src/lib/types.ts music_downloader/gui/frontend/src/lib/api.ts music_downloader/gui/frontend/src/App.svelte tests/test_gui_bridge.py tests/test_gui_covers.py tests/test_gui_documentation.py README.md AGENTS.md
```

Expected: no whitespace errors; the targeted source and test changes are visible alongside regenerated static assets and the two untracked design/plan documents. Do not run `git add` or `git commit`.
