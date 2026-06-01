import json

from music_downloader.display import display_results


def test_json_output_remains_plain_json(capsys):
    data = [{"id": "1", "name": "Song"}]

    display_results(data, "Song", output_format="json")

    captured = capsys.readouterr()
    assert json.loads(captured.out) == data
    assert captured.err == ""
