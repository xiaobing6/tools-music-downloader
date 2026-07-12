# GUI Visual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the desktop GUI's select controls, eliminate scrollbar layout shifts, and make the startup and workbench screens more visually focused without changing product behavior.

**Architecture:** Keep native HTML `<select>` controls for their browser popup, keyboard behavior, and accessibility, while wrapping them with a non-interactive Lucide chevron that rotates when Chromium exposes the native open state. Reserve the scroll gutter on the existing `.workbench-shell`; refine only CSS and component structure already responsible for the startup and workbench appearance.

**Tech Stack:** Svelte 5, TypeScript, Tailwind CSS, `@lucide/svelte`, Node built-in test runner, pytest, Vite.

## Global Constraints

- Do not modify `window.pywebview.api`, Python search/download behavior, or persisted GUI settings behavior.
- Keep native `<select>` elements, labels, names, focus treatment, and keyboard behavior intact.
- GUI default window size remains `1280x800`; the minimum remains `1024x720`; activity rail moves below results below `1180px`.
- All GUI copy remains Chinese; startup copy must not reveal browser, site-verification, or diagnostic details.
- Update source, tests, `README.md`, `AGENTS.md`, the existing design spec, and Vite static build output. Do not hand-edit `music_downloader/gui/static/`.

---

### Task 1: Lock the visual contracts in failing tests

**Files:**
- Modify: `music_downloader/gui/frontend/tests/startup.test.mjs`
- Modify: `tests/test_gui_static.py`
- Modify: `tests/test_gui_documentation.py`

**Interfaces:**
- Consumes: source text from `SettingsPanel.svelte`, `StartupScreen.svelte`, `app.css`, `README.md`, and `AGENTS.md`.
- Produces: regression assertions for select affordances, scroll-gutter stability, visual compactness, and documentation promises.

- [ ] **Step 1: Add the failing Node source-contract test.**

  Add a `readSettingsPanelSource()` helper and a test that asserts the settings panel imports `ChevronDown`, renders `select-control` and `select-chevron`, and marks the icon as decorative.

  ```js
  test("settings selects provide a decorative custom chevron", async () => {
    const source = await readSettingsPanelSource();
    assert.match(source, /ChevronDown/);
    assert.match(source, /class="select-control"/);
    assert.match(source, /class="select-chevron"/);
    assert.match(source, /aria-hidden="true"/);
  });
  ```

- [ ] **Step 2: Add failing Python source-contract tests.**

  Add one test that requires `.workbench-shell` to reserve its scrollbar gutter and a second that requires the compact startup tokens and grouped activity rail.

  ```python
  def test_workbench_reserves_a_stable_scrollbar_gutter() -> None:
      css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")
      shell_block = css.split(".workbench-shell {", 1)[1].split("}", 1)[0]
      assert "overflow-y: auto;" in shell_block
      assert "scrollbar-gutter: stable;" in shell_block
      assert "overflow-x: hidden;" in shell_block

  def test_visual_polish_keeps_startup_compact_and_activity_grouped() -> None:
      startup = (FRONTEND_SRC / "lib/components/StartupScreen.svelte").read_text(encoding="utf-8")
      css = (FRONTEND_SRC / "app.css").read_text(encoding="utf-8")
      assert "width: min(560px, calc(100% - 40px));" in startup
      assert "font-size: clamp(42px, 5vw, 48px);" in startup
      assert "opacity: 0.68;" in startup
      assert "background: rgba(255, 255, 255, 0.56);" in css
  ```

- [ ] **Step 3: Add the failing documentation contract.**

  Require README and AGENTS to state the stable scroll-gutter behavior and select-arrow enhancement.

  ```python
  assert "scrollbar-gutter" in readme
  assert "下拉箭头" in readme
  assert "scrollbar-gutter" in agents
  assert "下拉箭头" in agents
  ```

- [ ] **Step 4: Run the targeted tests and verify RED.**

  Run: `node --test music_downloader/gui/frontend/tests/startup.test.mjs; python -m pytest tests/test_gui_static.py tests/test_gui_documentation.py -q`

  Expected: FAIL because no `ChevronDown` select shell, `scrollbar-gutter`, compact startup values, activity grouping, or matching documentation exists yet.

### Task 2: Implement native select affordances and stable scrolling

**Files:**
- Modify: `music_downloader/gui/frontend/src/lib/components/SettingsPanel.svelte`
- Modify: `music_downloader/gui/frontend/src/app.css`

**Interfaces:**
- Consumes: `SelectItem`, existing select IDs and change callbacks.
- Produces: native selects inside `.select-control` shells and CSS for the decorative chevron and stable scroll gutter.

- [ ] **Step 1: Wrap each native select with a select shell.**

  Import `ChevronDown` from `@lucide/svelte`. Wrap `sourceSelect`, `typeSelect`, and `bitrateSelect` in `<span class="select-control">`; add `select-input` to each select; append `<ChevronDown class="select-chevron" size={16} strokeWidth={2.25} aria-hidden="true" />` after each select. Keep the existing `id`, `name`, option loops, disabled state, and `onchange` callbacks.

- [ ] **Step 2: Add the minimal CSS enhancement.**

  Add CSS that removes the platform arrow only for `.select-input`, reserves space for the icon, lets pointer events pass through the icon, and rotates the chevron only when support for `.select-control:has(select:open)` exists.

  ```css
  .select-control { position: relative; display: block; }
  .select-input { appearance: none; padding-right: 2.75rem; }
  .select-chevron { pointer-events: none; position: absolute; top: 50%; right: 0.75rem; transform: translateY(-50%); }
  @supports selector(.select-control:has(select:open)) {
    .select-control:has(select:open) .select-chevron { transform: translateY(-50%) rotate(180deg); }
  }
  ```

- [ ] **Step 3: Reserve the existing workbench scroll gutter.**

  Replace the generic `overflow: auto` in `.workbench-shell` with `overflow-y: auto`, `overflow-x: hidden`, and `scrollbar-gutter: stable`. Add an `@supports not (scrollbar-gutter: stable)` fallback with `overflow-y: scroll`.

- [ ] **Step 4: Run the targeted tests and verify GREEN.**

  Run: `node --test music_downloader/gui/frontend/tests/startup.test.mjs; python -m pytest tests/test_gui_static.py -q`

  Expected: PASS, proving the source exposes native-select enhancement and reserves the scrollbar footprint.

### Task 3: Compact the launch composition and unify the activity rail

**Files:**
- Modify: `music_downloader/gui/frontend/src/lib/components/StartupScreen.svelte`
- Modify: `music_downloader/gui/frontend/src/app.css`
- Modify: `music_downloader/gui/frontend/src/lib/components/EmptyState.svelte`

**Interfaces:**
- Consumes: existing startup stage props, color tokens, result-list empty state, and responsive activity rail.
- Produces: a shorter launch composition, a quieter header audio motif, a grouped desktop activity rail, and a more directive empty state.

- [ ] **Step 1: Compact the startup visual hierarchy.**

  Update the existing startup CSS to use a `560px` content width; a smaller mark, title, subtitle, status type, and progress bar; and a lower-opacity, lower-positioned wave. Preserve the `startup-*` selectors, stage copy, progress semantics, retry button, and reduced-motion rule.

  ```css
  .startup-content { width: min(560px, calc(100% - 40px)); padding: clamp(116px, 20vh, 190px) 0 clamp(44px, 6vh, 72px); }
  .startup-title { font-size: clamp(42px, 5vw, 48px); }
  .startup-subtitle { font-size: 20px; }
  .startup-wave { bottom: -72px; opacity: 0.68; }
  ```

- [ ] **Step 2: Reduce homepage header competition.**

  Tighten the command card spacing and make `.music-track` a short, muted signature line (`margin-left: auto`, `max-width: 160px`, reduced opacity) rather than a full-width visual divider. Preserve the green ready state as the only strong status accent.

- [ ] **Step 3: Group desktop activity cards and refine the empty state.**

  Give `.activity-rail` a soft translucent surface, thin border, 16px radius, and 12px inner gap at desktop widths. In the existing `max-width: 1179px` rule, remove that shell so the moved activity section remains lightweight. Change the empty-state supporting copy to direct the first action without adding new click behavior.

- [ ] **Step 4: Run visual and code verification.**

  Run: `npm.cmd --prefix music_downloader/gui/frontend run check; node --test music_downloader/gui/frontend/tests/startup.test.mjs; python -m pytest tests/test_gui_static.py -q`

  Expected: all commands PASS.

### Task 4: Synchronize documentation, build artifacts, and visual verification

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md`
- Modify: `music_downloader/gui/static/` via Vite build output only

**Interfaces:**
- Consumes: the implemented visual contract.
- Produces: maintainer-facing documentation and packaged static assets consistent with source.

- [ ] **Step 1: Update documentation.**

  State that the workbench reserves a stable scrollbar gutter; native selects use a consistent decorative down arrow that rotates upward when the open state is exposed; the startup page is intentionally compact; and the desktop activity rail uses a shared soft surface.

- [ ] **Step 2: Run documentation tests and verify GREEN.**

  Run: `python -m pytest tests/test_gui_documentation.py -q`

  Expected: PASS.

- [ ] **Step 3: Build frontend static assets.**

  Run: `npm.cmd --prefix music_downloader/gui/frontend run build`

  Expected: Svelte check and Vite build complete successfully, regenerating `music_downloader/gui/static/`.

- [ ] **Step 4: Render visual regression states.**

  Use a mocked `window.pywebview.api` and Playwright to render startup, default workbench, and expanded settings at `1280x800`; render default and expanded workbench at `1024x720`. Confirm: no horizontal overflow; opening settings does not shift the shell width; native chevrons remain legible; the startup status does not collide with the wave; and the desktop activity cards share a soft grouping surface.

- [ ] **Step 5: Run final targeted verification.**

  Run: `node --test music_downloader/gui/frontend/tests/startup.test.mjs; python -m pytest tests/test_gui_static.py tests/test_gui_documentation.py tests/test_gui_app.py -q; git diff --check`

  Expected: all checks PASS with no whitespace errors.

### Task 5: Replace the outer scrollbar gutter with a fixed application shell

**Files:**
- Modify: `music_downloader/gui/frontend/src/app.css`
- Modify: `tests/test_gui_static.py`
- Modify: `tests/test_gui_documentation.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md`
- Modify: `music_downloader/gui/static/` via Vite build output only

**Interfaces:**
- Consumes: the existing `.workbench-shell`, `.workbench-frame`, `.workbench-main`, responsive activity rail, and internal result/log scrollers.
- Produces: an outer shell with equal per-breakpoint padding and no window-level scrollbar; the lower workspace owns responsive overflow.

- [ ] **Step 1: Replace the old source-contract tests with fixed-shell assertions.**

  Require `.workbench-shell` to use `overflow: hidden`, `.workbench-frame` to use `height: 100%`, `min-height: 0`, and `box-sizing: border-box`, and the narrow `.workbench-main` to use `overflow-y: auto` with contained overscroll. Update documentation tests to reject `scrollbar-gutter` and require the phrase `固定外壳`.

- [ ] **Step 2: Run the targeted tests and verify RED.**

  Run: `python -m pytest tests/test_gui_static.py::test_workbench_uses_fixed_shell_with_internal_scrolling tests/test_gui_documentation.py::test_gui_docs_cover_visual_polish_contract -q`

  Expected: FAIL because the outer shell still owns scrolling and documentation still promises `scrollbar-gutter`.

- [ ] **Step 3: Implement the fixed-height shell.**

  ```css
  .workbench-shell { overflow: hidden; }
  .workbench-frame { box-sizing: border-box; height: 100%; min-height: 0; }
  .workbench-main { overflow: hidden; }
  @media (max-width: 1179px) {
    .workbench-main { min-height: 0; overflow-y: auto; overscroll-behavior: contain; }
  }
  ```

  Keep desktop padding at `16px` on all four sides and narrow padding at `12px` on all four sides. Opening more settings consumes height from `.workbench-main`; result and log content continue scrolling in their existing internal containers.

- [ ] **Step 4: Update documentation and build output.**

  Replace the scrollbar-gutter description with the fixed-shell and internal-workspace scrolling contract in README, AGENTS, and the current design spec. Run `npm.cmd --prefix music_downloader/gui/frontend run build` to regenerate static assets.

- [ ] **Step 5: Render both supported window sizes.**

  At `1280x800` and `1024x720`, capture collapsed and expanded settings. Assert the frame rectangle remains inset equally on all four sides, the shell has no window-level overflow, and the narrow lower workspace remains scrollable.

### Task 6: Convert search results into a compact desktop music library

**Files:**
- Modify: `music_downloader/gui/frontend/src/lib/components/ResultList.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/components/SearchBar.svelte`
- Modify: `music_downloader/gui/frontend/src/App.svelte`
- Modify: `music_downloader/gui/frontend/src/app.css`
- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs`
- Modify: `tests/test_gui_static.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md`
- Modify: `music_downloader/gui/static/` via Vite build output only

**Interfaces:**
- Consumes: existing `Song`, `SongStatus`, selection callbacks, and fixed-shell result workspace.
- Produces: compact 60px result rows with song, album, source/status, and duration columns; visible selected/focus states; one consolidated result count.

- [ ] **Step 1: Add failing source-contract tests.**

  Require `.result-columns`, `.result-row`, `data-selected`, `focus-visible`, `40px` artwork, human-readable source labels, an em dash for unknown duration, and a combined `共 N 首 · 已选择 N 首` summary. Require `SearchBar` and `App.svelte` to stop passing or rendering `resultCount`.

- [ ] **Step 2: Verify RED.**

  Run: `node --test music_downloader/gui/frontend/tests/workbench.test.mjs`

  Expected: FAIL because the current list uses 48px artwork, a three-line card-like row, repeated source badges, and duplicate result count output.

- [ ] **Step 3: Implement the compact library rows.**

  Use a shared six-column CSS grid for the column header and rows: checkbox, 40px artwork, song/artist, album, source/status, and duration. Set row minimum height to `60px`, keep truncation on user content, show plain muted Chinese source labels, render unknown durations as `—`, and show selected rows with a pale blue background plus a 3px inset brand line.

- [ ] **Step 4: Improve focus and action feedback.**

  Add a `focus-within` row treatment, switch checkbox focus to `focus-visible`, and show the selected count in the download action label. Preserve the full-row checkbox hit target.

- [ ] **Step 5: Consolidate search result counts.**

  Remove the visible result count prop and status text from `SearchBar`; keep a screen-reader live search status. Show total and selected counts together in the result panel header.

- [ ] **Step 6: Update docs, build, and render.**

  Document the compact library layout and selection treatment, rebuild Vite static assets, and render populated result lists at `1280x800` and `1024x720`. Confirm at least five complete rows remain visible in the wide default window, column alignment is stable, selected rows are obvious, and no horizontal overflow appears.

### Task 7: Rebalance result columns and stabilize the download action

**Files:**
- Modify: `music_downloader/gui/frontend/src/app.css`
- Modify: `music_downloader/gui/frontend/src/lib/components/ResultList.svelte`
- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs`
- Modify: `tests/test_gui_static.py`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md`
- Modify: `music_downloader/gui/static/` via Vite build output only

**Interfaces:**
- Consumes: the existing six-column `.result-columns` / `.result-row` grid and `selectedCount` summary.
- Produces: content-weighted song, album, source/status, and duration tracks plus a width-stable download action.

- [ ] **Step 1: Write failing source-contract tests.**

  Require the shared grid to use `16px 40px minmax(190px, 1fr) minmax(180px, 0.95fr) minmax(150px, 0.72fr) 64px`. Require the download button to contain the literal `下载选中` and reject the dynamic count interpolation.

- [ ] **Step 2: Run the tests and verify RED.**

  Run: `node --test music_downloader/gui/frontend/tests/workbench.test.mjs; python -m pytest tests/test_gui_static.py::test_result_list_uses_compact_library_rows -q`

  Expected: FAIL because the grid still overweights the song column and the button still renders `selectedCount`.

- [ ] **Step 3: Implement the balanced grid and stable label.**

  Change the shared grid tracks to:

  ```css
  grid-template-columns: 16px 40px minmax(190px, 1fr) minmax(180px, 0.95fr) minmax(150px, 0.72fr) 64px;
  ```

  Render `下载选中` without a counter. Keep `共 {songs.length} 首 · 已选择 {selectedCount} 首` as the only selected-count display.

- [ ] **Step 4: Verify GREEN and update artifacts.**

  Run the Node and Python tests, update README/AGENTS/design documentation to describe content-weighted columns and a stable action label, then run `npm.cmd --prefix music_downloader/gui/frontend run build`.

- [ ] **Step 5: Render both supported window sizes.**

  Render populated results at `1280x800` and `1024x720`. Confirm no horizontal overflow, the song column is no longer disproportionately wide, the source/status column has room for secondary status, the `64px` duration column stays right-aligned, and selecting 0, 1, or all rows does not move the action group.

### Task 8: Replace the native close prompt with a themed application modal

**Files:**
- Create: `music_downloader/gui/frontend/src/lib/components/CloseConfirmModal.svelte`
- Modify: `music_downloader/gui/app.py`
- Modify: `music_downloader/gui/api.py`
- Modify: `music_downloader/gui/frontend/src/App.svelte`
- Modify: `music_downloader/gui/frontend/src/lib/api.ts`
- Modify: `music_downloader/gui/frontend/src/lib/types.ts`
- Modify: `tests/test_gui_app.py`
- Modify: `tests/test_gui_api.py`
- Modify: `music_downloader/gui/frontend/tests/workbench.test.mjs`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/superpowers/specs/2026-07-12-music-workbench-frontend-design.md`
- Modify: `music_downloader/gui/static/` via Vite build output only

**Interfaces:**
- Consumes: pywebview `closing`/`closed` events, `MusicApi._emit`, and the existing Flowbite modal system.
- Produces: `py-close-request` browser events, `PywebviewApi.confirm_close()`, and a themed global close confirmation modal.

- [ ] **Step 1: Write failing backend and frontend contract tests.**

  Require native `confirm_close` to be disabled, the first `closing` event to return cancellation and emit `py-close-request`, and the one-shot confirmed close to allow destruction. Require a `CloseConfirmModal` with `role="alertdialog"`, the exact copy “关闭音乐下载器？” / “确定要关闭应用吗？”, safe default focus, Escape/backdrop dismissal, and “继续使用” / “关闭应用” actions.

- [ ] **Step 2: Verify RED.**

  Run: `python -m pytest tests/test_gui_app.py tests/test_gui_api.py -q; node --test music_downloader/gui/frontend/tests/workbench.test.mjs`

  Expected: FAIL because closing still uses the native prompt and no frontend close-request bridge or modal exists.

- [ ] **Step 3: Implement the one-shot close protocol.**

  Add `MusicApi.request_close_confirmation()`, `MusicApi.consume_close_confirmation()`, and public `MusicApi.confirm_close()`. The native `closing` handler cancels and emits a browser request unless the one-shot confirmation flag has been armed; the `closed` handler remains the only place that calls `shutdown()`.

- [ ] **Step 4: Implement the themed modal.**

  Add a compact Flowbite modal matching the workbench card radius, border, shadow, blue icon treatment, and red destructive action. Bind `open`, autofocus “继续使用”, allow Escape/backdrop dismissal, prevent repeated confirm clicks, and expose `onConfirm`.

- [ ] **Step 5: Connect the frontend bridge.**

  Add `onCloseRequest()` to `src/lib/api.ts`, add `confirm_close()` to `PywebviewApi`, subscribe in `App.svelte`, and render the modal globally so it also works during startup.

- [ ] **Step 6: Update docs, build, and verify visually.**

  Replace native-prompt documentation with the themed close protocol, rebuild static assets, render the modal at `1280x800` and `1024x720`, and verify focus, Escape, backdrop cancellation, confirm action, and no premature shutdown.
