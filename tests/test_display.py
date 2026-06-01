import json

import music_downloader.display as display
from music_downloader.display import display_results


def test_json_output_remains_plain_json(capsys):
    data = [{"id": "1", "name": "Song"}]

    display_results(data, "Song", output_format="json")

    captured = capsys.readouterr()
    assert json.loads(captured.out) == data
    assert captured.err == ""


def test_table_output_falls_back_without_rich(monkeypatch, capsys):
    monkeypatch.setattr(display, "RichTable", None)

    display.display_results([{"id": "1", "name": "Song"}], "Song", output_format="table")

    captured = capsys.readouterr()
    assert "Song" in captured.out
