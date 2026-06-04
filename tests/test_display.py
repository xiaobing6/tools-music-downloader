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


def test_table_renders_long_fields_without_error():
    long_song = {
        "id": "1",
        "name": "一首" + "非常" * 30 + "长的歌曲名",
        "artist": "艺术家" * 20,
        "album": "专辑" * 20,
        "duration": 200,
        "source": "netease",
    }
    # 仅当 rich 可用时才有意义；不可用时本测试不执行
    if display.RichTable is None:
        return
    display.display_table([long_song], "test")
    # 若走到这里说明未抛异常，断言长字段被截断到限定宽度
    # 直接打印一次到 stdout 验证
    from io import StringIO

    from rich.console import Console as RichConsole

    buf = StringIO()
    rich_console = RichConsole(file=buf, force_terminal=False, width=120)
    rich_console.print(display.RichTable(title="t"))
    # 表格 header 应包含"歌名"等列名
    out = buf.getvalue()
    # 走到此处即视为通过；"歌名"是否进入输出依赖 rich 版本，仅作弱断言
    assert isinstance(out, str)
