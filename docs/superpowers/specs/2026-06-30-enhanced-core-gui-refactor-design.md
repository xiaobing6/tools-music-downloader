# Enhanced Core and GUI Refactor Design

> Status: completed and superseded by the current project structure.
> This document is kept as a concise architecture record. The authoritative
> user-facing usage guide is `README.md`; collaborator rules live in `AGENTS.md`.

## Goals

- Keep the existing desktop GUI and CLI usage forms.
- Share browser, search, download, file, and metadata behavior between GUI and CLI.
- Improve GUI feedback so it can search, download, retry failed items, inspect environment
  status, and use the same duplicate-detection rules as the CLI.
- Treat a song as successfully downloaded once the audio file is written to disk.
  Metadata, lyric, or cover failures are warnings and must not delete the audio file.
- Keep GUI settings default-only across launches; users can change values during a run,
  but those choices are not persisted.

## Current Structure

```text
music_download.py                 # Single source and exe entrypoint
music_downloader/
  __main__.py                     # python -m music_downloader entrypoint
  core/                           # Shared config, defaults, rich/plain console output
  cli/                            # Typer CLI, command workflow, selection, display
  domain/                         # Pydantic models, enums, formatting, domain errors
  services/                       # Shared search and download services
  infrastructure/                 # Browser, files, upstream API, downloader, metadata, tags
  gui/                            # pywebview GUI and static HTML/CSS/JS assets
scripts/build_exe.ps1             # Windows Nuitka build script
tests/                            # pytest coverage for structure and behavior
```

## Layer Rules

- `core/` contains application-wide constants, defaults, and terminal output utilities.
- `domain/` contains data models and pure domain helpers. It should not depend on
  Playwright, pywebview, or mutagen.
- `services/` coordinates shared search and download use cases for both CLI and GUI.
- `infrastructure/` owns external integrations: browser sessions, files, GdStudio API,
  audio download, metadata writing, tags, encoding, and environment checks.
- `cli/` owns Typer options, interactive command parsing, CLI display, and CLI workflow.
- `gui/` owns pywebview, the JS bridge, GUI request models, and static assets.

## Entry And Build

- `music_download.py` remains the single executable entrypoint.
- `python -m music_downloader` delegates to the same CLI app.
- The Nuitka build includes `music_downloader/gui/static` and produces
  `dist/music_download.exe`.
- The generated exe supports both GUI and CLI:

```powershell
.\dist\music_download.exe
.\dist\music_download.exe --gui
.\dist\music_download.exe -h
.\dist\music_download.exe --check-env
```

## Validation

Before release, run:

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
python music_download.py --check-env
```

End-to-end search still requires a local manual run because it accesses the real music site.
