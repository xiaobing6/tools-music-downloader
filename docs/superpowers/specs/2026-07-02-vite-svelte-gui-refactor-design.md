# Vite Svelte GUI Refactor Design

> Status: approved for planning.
> User-facing usage stays in `README.md`; collaborator rules stay in `AGENTS.md`.

## Goals

- Refactor the existing pywebview GUI to a Vite + Svelte frontend.
- Use TypeScript for frontend state, pywebview bridge types, and event payloads.
- Use a finished-component UI style, with Flowbite Svelte as the primary component library.
- Keep all existing GUI behavior: browser initialization, search, selection, batch download,
  failed-download retry, cancellation, directory selection, directory opening, environment
  checks, progress display, and logs.
- Keep pywebview as the desktop shell and keep Python as the owner of browser, search,
  download, file, and metadata behavior.
- Set the GUI default window to `1280x800` and the minimum window size to `1200x750`.
- Keep the final static frontend output under `music_downloader/gui/static/` so Nuitka can
  package it with the existing data-file strategy.
- Fix compiled-exe static-resource resolution so onefile and standalone builds can find
  `static/index.html`.

## Non-Goals

- Do not introduce Electron, Tauri, Qt, or a second desktop shell.
- Do not change CLI behavior or shared download semantics.
- Do not persist GUI option changes across launches.
- Do not change the upstream `music.gdstudio.org` API integration.
- Do not add new user-facing features beyond the equivalent behavior needed by the refactor.

## Frontend Stack

- `Vite` builds the frontend from source to static assets.
- `Svelte` owns component structure and reactive UI state.
- `TypeScript` defines GUI config, song result, progress event, log event, environment check,
  and pywebview API types.
- `Flowbite Svelte` provides finished UI components for buttons, inputs, selects, modals,
  badges, progress bars, tables/lists, alerts, and tooltips.
- `Tailwind CSS` supports Flowbite styling and focused custom layout rules.
- `lucide-svelte` provides icons for commands such as search, download, retry, folder,
  settings, check, warning, cancel, and log controls.

## Directory Layout

```text
music_downloader/gui/
  app.py                         # pywebview window and static asset lookup
  api.py                         # Python API exposed to JavaScript
  bridge.py                      # Python orchestration and Playwright thread
  settings.py                    # default-only GUI config
  frontend/                      # Svelte/Vite source
    package.json
    tsconfig.json
    vite.config.ts
    index.html
    src/
      App.svelte
      main.ts
      app.css
      lib/
        api.ts                   # typed pywebview bridge wrapper
        types.ts                 # shared frontend data contracts
        state.ts                 # UI state helpers
        components/
          SearchBar.svelte
          SettingsPanel.svelte
          ResultList.svelte
          DownloadProgress.svelte
          LogPanel.svelte
          EnvironmentModal.svelte
          EmptyState.svelte
  static/                        # generated Vite output consumed by pywebview/Nuitka
```

`static/` remains the runtime asset directory. The build script should run the frontend build
before Nuitka packaging, and Vite should emit directly into `music_downloader/gui/static/`.

## User Interface

The first screen remains the usable application, not a landing page.

- Top area: search input, search button, and compact result count.
- Left settings panel: source, search type, bitrate, result count, cover/lyric toggles,
  output directory, browse button, open-directory button, and environment-check command.
- Main result area: dense searchable-result list with cover, title, artist, album, duration,
  source badge, quality badge, checkbox state, and per-song download status.
- Bottom utility area: download progress and logs. Logs should be available but visually
  secondary, with collapse behavior preserved.
- Modal: environment check results with clear success/failure status.
- Empty, loading, error, downloading, skipped, failed, and success states must be explicit.

The layout should be designed for the new minimum size of `1200x750`. It may grow cleanly on
larger displays, but does not need a compact mobile layout because this is a desktop app.

## Python Integration

`music_downloader/gui/app.py` remains the only GUI entry point. It should:

- Resolve static files correctly when running from source.
- Resolve static files correctly in Nuitka standalone builds.
- Resolve static files correctly in Nuitka onefile builds.
- Create the pywebview window with default size `1280x800`.
- Set `min_size=(1200, 750)`.
- Continue exposing `MusicApi` through `js_api`.

`music_downloader/gui/api.py` and `bridge.py` should keep their public behavior stable. The
Svelte app should call the same pywebview methods currently used by `app.js`:

- `get_valid_options`
- `get_config`
- `save_config`
- `init_browser`
- `search`
- `start_download`
- `cancel_download`
- `select_directory`
- `open_download_dir`
- `check_environment`

The frontend should listen for the same custom events:

- `py-log`
- `py-progress`

## Build And Packaging

The build flow should be:

```text
Svelte source -> Vite build -> music_downloader/gui/static -> Nuitka include-data-dir -> exe
```

`scripts/build_exe.ps1` should:

- Install or verify frontend dependencies when needed.
- Run the Vite production build before Nuitka.
- Keep including `music_downloader/gui/static` in the Nuitka data files.
- Fail early if the frontend build does not produce `static/index.html`.

The repository should include Node package metadata needed to reproduce the frontend build.
Generated `node_modules/` must not be committed. Generated static output may remain committed
if the project wants source checkout GUI runs to work without Node; otherwise README must make
the frontend build prerequisite explicit. For this project, generated static output should
remain available because `python music_download.py --gui` currently expects static files.

## Error Handling

- If pywebview is not ready, the frontend should show a clear GUI error and log it.
- If browser initialization fails, the search/download controls should remain disabled or
  guarded until initialization succeeds.
- If search fails, existing results should not be silently replaced by a misleading success
  state.
- If a download item fails, it should be marked retryable and included in failed retry logic.
- If metadata, lyric, or cover writing fails, the existing warning-only download success
  semantics remain unchanged.
- If static assets are missing, the Python startup error should list the checked candidate
  paths so packaging issues are diagnosable.

## Testing And Verification

Focused tests should cover:

- Static entry generation: `music_downloader/gui/static/index.html` exists after frontend build.
- GUI static content contains the application mount point and built module assets.
- `app.py` static path resolution handles source and compiled-style candidate paths.
- Existing retry-failed behavior remains represented in the frontend source or built output.
- Python checks still pass for the unchanged backend and bridge layers.

Before release, run:

```powershell
npm --prefix music_downloader/gui/frontend run build
npm --prefix music_downloader/gui/frontend run check
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
.\scripts\build_exe.ps1 -SkipInstall
.\dist\music_download.exe --check-env
```

A manual GUI smoke test should verify: app launches from source, app launches from the compiled
exe, browser initialization completes or gives a readable Cloudflare/Chrome error, search
returns results, selected downloads start, cancellation works, failed retry remains available,
and environment check opens in a modal.
