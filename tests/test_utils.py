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
    assert sanitize_filename('CON.mp3') == "_CON.mp3"
    assert sanitize_filename('[1] A/B:C*D?"E<F>G|.mp3') == "[1] A_B_C_D__E_F_G_.mp3"
    assert sanitize_filename("  ...  ") == "download"


def test_parse_selection_accepts_ranges_and_ignores_bad_values():
    assert parse_selection("1, 3, 5-7, x, 99", 6) == [0, 2, 4, 5]
    assert parse_selection("4-2", 5) == [1, 2, 3]
