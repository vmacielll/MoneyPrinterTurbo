import os
import tempfile

from app.services.subtitle import parse_subtitle_cues


def _write_srt(path, srt_text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(srt_text)


SRT = """1
00:00:00,000 --> 00:00:02,500
Hello world

2
00:00:02,500 --> 00:00:05,000
Second line
"""


def test_parse_subtitle_cues_returns_ordered_float_times():
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "sub.srt")
        _write_srt(p, SRT)
        cues = parse_subtitle_cues(p)
    assert cues == [
        (0.0, 2.5, "Hello world"),
        (2.5, 5.0, "Second line"),
    ]


def test_parse_subtitle_cues_missing_file_returns_empty():
    assert parse_subtitle_cues("/no/such/file.srt") == []


def test_parse_subtitle_cues_trailing_block_without_blank_line():
    # file_to_subtitles flushes a final block with no trailing blank line
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "sub.srt")
        _write_srt(p, "1\n00:00:00,000 --> 00:00:01,000\nOnly line\n")
        cues = parse_subtitle_cues(p)
    assert cues == [(0.0, 1.0, "Only line")]