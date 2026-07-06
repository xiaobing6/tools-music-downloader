# CLI Help Details Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `python music_download.py -h` show valid CLI option values for music source, search type, output format, and bitrate.

**Architecture:** Keep the public Typer CLI in `music_downloader/cli/app.py`. Generate help text from existing constants in `music_downloader/core/config.py` so future option-list changes automatically reach `--help`. Add tests in `tests/test_cli_app.py`; do not change argument forwarding or runtime behavior.

**Tech Stack:** Python 3.10+, Typer, pytest.

---

### Task 1: Detailed Typer Help Text

**Files:**
- Modify: `tests/test_cli_app.py`
- Modify: `music_downloader/cli/app.py`

- [x] **Step 1: Write the failing help-output test**

Add imports and assertions to `tests/test_cli_app.py` so the test checks every supported value appears in `--help`.

```python
from music_downloader.core.config import (
    SEARCH_TYPE_MAP,
    VALID_BITRATES,
    VALID_FORMATS,
    VALID_SOURCES,
)
```

```python
def test_help_lists_supported_option_values() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    for value in VALID_SOURCES:
        assert value in result.output
    for value in SEARCH_TYPE_MAP:
        assert value in result.output
    for value in VALID_FORMATS:
        assert value in result.output
    for value in VALID_BITRATES:
        assert value in result.output
    assert "downloads" in result.output
    assert ".chrome-profile" in result.output
```

- [x] **Step 2: Run the focused test to verify it fails**

Run: `python -m pytest tests/test_cli_app.py::test_help_lists_supported_option_values -q`

Expected: FAIL because the current Typer help output does not include all values such as `migu`, `album`, `json`, or `flac`.

- [x] **Step 3: Add help text helpers**

In `music_downloader/cli/app.py`, import option constants and add a helper for formatting value lists.

```python
from music_downloader.core.config import (
    DEFAULT_BITRATE,
    DEFAULT_KEYWORD,
    DEFAULT_NUMBER,
    DEFAULT_SOURCE,
    SEARCH_TYPE_MAP,
    VALID_BITRATES,
    VALID_FORMATS,
    VALID_SOURCES,
)
```

```python
def _value_list(values: list[str] | tuple[str, ...]) -> str:
    return " / ".join(values)
```

- [x] **Step 4: Update Typer option help strings**

Change the option help strings in `main_command`:

```python
source: Annotated[
    str,
    typer.Option(
        "-s",
        "--source",
        help=f"音乐源，可选: {_value_list(VALID_SOURCES)}",
    ),
] = DEFAULT_SOURCE,
```

```python
search_type: Annotated[
    str,
    typer.Option(
        "-t",
        "--type",
        help=f"搜索类型，可选: {_value_list(tuple(SEARCH_TYPE_MAP))}",
    ),
] = "song",
```

```python
output_dir: Annotated[
    str,
    typer.Option("-o", "--output", help="下载目录，默认使用项目 downloads/"),
] = "",
```

```python
output_format: Annotated[
    str,
    typer.Option("-f", "--format", help=f"输出格式，可选: {_value_list(VALID_FORMATS)}"),
] = "table",
```

```python
bitrate: Annotated[
    str,
    typer.Option("-b", "--bitrate", help=f"音质选择，可选: {_value_list(VALID_BITRATES)}"),
] = DEFAULT_BITRATE,
```

```python
user_data_dir: Annotated[
    str | None,
    typer.Option("--user-data-dir", help="自定义 Chrome 用户数据目录，默认使用项目 .chrome-profile/"),
] = None,
```

Keep Rich help rendering enabled on `typer.Typer(...)`, keep option-row help short, and put the complete supported value lists in `epilog` paragraphs. This preserves the colored Rich help table while avoiding ellipses in long option rows.

- [x] **Step 5: Run focused tests**

Run: `python -m pytest tests/test_cli_app.py -q`

Expected: PASS.

- [x] **Step 6: Inspect actual help output**

Run: `python .\music_download.py -h`

Expected: Help output includes values for `--source`, `--type`, `--format`, and `--bitrate`.

- [x] **Step 7: Run full verification**

Run:

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy music_downloader
python -m py_compile music_download.py
```

Expected: all commands pass.

- [x] **Step 8: Commit implementation**

```powershell
git add music_downloader/cli/app.py tests/test_cli_app.py docs/superpowers/plans/2026-07-06-cli-help-details.md
git commit -m "fix(cli): show supported values in help"
```
