from __future__ import annotations

from pathlib import Path

from music_downloader.gui import app


def test_candidate_static_dirs_include_module_static_first(tmp_path: Path) -> None:
    module_file = tmp_path / "music_downloader" / "gui" / "app.py"
    executable = tmp_path / "dist" / "music_download.exe"

    candidates = app._candidate_static_dirs(module_file=module_file, executable=executable)

    assert candidates[0] == module_file.parent / "static"
    assert executable.parent / "music_downloader" / "gui" / "static" in candidates
    assert executable.parent / "static" in candidates


def test_get_static_dir_returns_existing_candidate(tmp_path: Path) -> None:
    static_dir = tmp_path / "music_downloader" / "gui" / "static"
    static_dir.mkdir(parents=True)
    (static_dir / "index.html").write_text("<div id='app'></div>", encoding="utf-8")

    result = app._get_static_dir(
        module_file=tmp_path / "other" / "gui" / "app.py",
        executable=tmp_path / "music_download.exe",
    )

    assert result == str(static_dir)


def test_window_size_constants_match_designed_minimum() -> None:
    assert app.DEFAULT_WINDOW_SIZE == (1280, 800)
    assert app.MIN_WINDOW_SIZE == (1200, 750)
