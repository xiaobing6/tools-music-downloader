from music_downloader.utils import (
    format_duration,
    parse_selection,
    sanitize_filename,
    url_encode,
)


def test_url_encode_matches_api_expectations():
    assert url_encode("周杰伦 (Live)!") == "%E5%91%A8%E6%9D%B0%E4%BC%A6%20%28Live%29%21"


def test_format_duration_handles_empty_and_seconds():
    assert format_duration(0) == "--:--"
    assert format_duration(None) == "--:--"
    assert format_duration(125) == "2:05"


def test_sanitize_filename_handles_windows_rules():
    assert sanitize_filename("CON.mp3") == "_CON.mp3"
    assert sanitize_filename('[1] A/B:C*D?"E<F>G|.mp3') == "[1] A_B_C_D__E_F_G_.mp3"
    assert sanitize_filename("  ...  ") == "download"
    # 大小写不敏感
    assert sanitize_filename("con.mp3") == "_con.mp3"


def test_sanitize_filename_truncates_long_names():
    long_name = "a" * 500 + ".mp3"
    out = sanitize_filename(long_name)
    # 加上扩展名也仍在 max_length=180 限制内
    assert len(out) <= 180


def test_parse_selection_accepts_ranges_and_ignores_bad_values():
    assert parse_selection("1, 3, 5-7, x, 99", 6) == [0, 2, 4, 5]
    assert parse_selection("4-2", 5) == [1, 2, 3]


def test_parse_selection_warns_on_reversed_range():
    messages: list = []
    result = parse_selection("5-2", 6, warn=messages.append)
    assert result == [1, 2, 3, 4]
    assert any("反转区间 5-2 为 2-5" in msg for msg in messages)


def test_parse_selection_no_warn_when_in_order():
    messages: list = []
    parse_selection("1-3", 6, warn=messages.append)
    assert messages == []
