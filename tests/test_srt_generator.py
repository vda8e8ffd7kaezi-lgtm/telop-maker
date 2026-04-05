"""SRTジェネレーターのユニットテスト"""

from src.srt_generator import _format_timecode, generate_srt
from src.transcriber import Segment


def test_format_timecode_zero():
    assert _format_timecode(0) == "00:00:00,000"


def test_format_timecode_seconds():
    assert _format_timecode(5.5) == "00:00:05,500"


def test_format_timecode_minutes():
    assert _format_timecode(65.123) == "00:01:05,123"


def test_format_timecode_hours():
    assert _format_timecode(3661.0) == "01:01:01,000"


def test_generate_srt_single_segment():
    segments = [Segment(index=1, start=1.0, end=3.5, text="こんにちは")]
    result = generate_srt(segments)
    lines = result.strip().split("\n")
    assert lines[0] == "1"
    assert lines[1] == "00:00:01,000 --> 00:00:03,500"
    assert lines[2] == "こんにちは"


def test_generate_srt_multiple_segments():
    segments = [
        Segment(index=1, start=0.0, end=2.0, text="最初のセグメント"),
        Segment(index=2, start=3.0, end=5.0, text="次のセグメント"),
    ]
    result = generate_srt(segments)
    assert "1\n00:00:00,000 --> 00:00:02,000\n最初のセグメント" in result
    assert "2\n00:00:03,000 --> 00:00:05,000\n次のセグメント" in result


def test_generate_srt_empty():
    result = generate_srt([])
    assert result == ""
