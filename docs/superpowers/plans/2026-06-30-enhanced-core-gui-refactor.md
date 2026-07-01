# Enhanced Core and GUI Refactor Implementation Record

> Status: completed. The original task checklist has been replaced with this
> current-state record so the repository documentation does not point future
> contributors at obsolete paths.

## Implemented Structure

```text
music_downloader/
  core/
    config.py
    console.py
  cli/
    app.py
    workflow.py
    interactive.py
    display.py
    models.py
    selection.py
  domain/
    enums.py
    errors.py
    formatting.py
    models.py
  services/
    search.py
    download.py
  infrastructure/
    browser.py
    downloader.py
    encoding.py
    environment.py
    files.py
    gdstudio.py
    metadata.py
    tags.py
  gui/
    app.py
    api.py
    bridge.py
    settings.py
    static/
```

## Implemented Behavior

- GUI and CLI both use shared search and download services.
- GUI defaults reset on every launch and are not written to a user config file.
- GUI and CLI both use the project `downloads/` directory by default.
- Duplicate detection is based on the final target audio file already existing.
- Audio file creation is the success boundary for a song download.
- Metadata, cover, and lyric failures are warnings only.
- The root package no longer contains old implementation modules; normal code lives under
  `core/`, `cli/`, `domain/`, `services/`, `infrastructure/`, and `gui/`.

## Verification Commands

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
python music_download.py --check-env
python music_download.py -h
python -m music_downloader -h
```

For build verification:

```powershell
.\scripts\build_exe.ps1 -SkipInstall
.\dist\music_download.exe -h
.\dist\music_download.exe --check-env
```
