# CLI Help Details Design

## Goal

Improve `python music_download.py -h` / `--help` so users can see valid parameter values directly from the CLI help output, especially for options such as `--source`, `--type`, `--format`, and `--bitrate`.

## Scope

This change only improves help text. It must not change search, download, GUI startup, argument forwarding, or validation behavior.

## Current Behavior

The public CLI entrypoint is `music_downloader/cli/app.py`, implemented with Typer. It declares `--source`, `--type`, `--format`, and `--bitrate` as plain string options with short labels such as "music source" and "output format". As a result, `-h` only shows `TEXT` and does not show the valid values.

The lower-level workflow parser in `music_downloader/cli/workflow.py` already has `choices` for these options, but that parser is not what users see when calling the Typer help output.

## Design

Enhance `music_downloader/cli/app.py` help strings so they include valid values and defaults:

- `--source`: list values from `VALID_SOURCES`, default from `DEFAULT_SOURCE`.
- `--type`: list keys from `SEARCH_TYPE_MAP`, default `song`.
- `--format`: list values from `VALID_FORMATS`, default `table`.
- `--bitrate`: list values from `VALID_BITRATES`, default from `DEFAULT_BITRATE`.
- `--output`: mention the default download directory behavior.
- `--user-data-dir`: mention the default isolated Chrome profile directory.

The help strings should be generated from existing constants instead of duplicating hard-coded lists where practical.

## Testing

Add or extend CLI help tests in `tests/test_cli_app.py`:

- `--help` exits successfully.
- The help output includes representative options already covered today.
- The help output includes all supported values for sources, search types, formats, and bitrates.
- `-h` remains supported.

No network calls should be used for these tests.

## Documentation

README already lists the main option values, so no README change is required unless the final help wording introduces new behavior.
