import pytest

from ytnotes.cli import slugify
from ytnotes.youtube import Segment, extract_video_id, fmt_ts, group_segments

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        VID,
        f"https://www.youtube.com/watch?v={VID}",
        f"https://www.youtube.com/watch?v={VID}&t=42s&list=abc",
        f"youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}?si=share",
        f"https://youtube.com/shorts/{VID}",
        f"https://www.youtube.com/embed/{VID}",
        f"https://m.youtube.com/live/{VID}",
        f"https://www.youtube-nocookie.com/embed/{VID}",
    ],
)
def test_extract_video_id(url):
    assert extract_video_id(url) == VID


@pytest.mark.parametrize("url", ["https://vimeo.com/123", "https://youtube.com/", "not a url"])
def test_extract_video_id_rejects(url):
    with pytest.raises(ValueError):
        extract_video_id(url)


def test_fmt_ts():
    assert fmt_ts(0) == "00:00"
    assert fmt_ts(754.9) == "12:34"
    assert fmt_ts(3725) == "1:02:05"


def test_group_segments_merges_into_windows():
    segs = [Segment(0, "a"), Segment(10, "b"), Segment(31, "c"), Segment(40, "d")]
    grouped = group_segments(segs, window=30)
    assert [(g.start, g.text) for g in grouped] == [(0, "a b"), (31, "c d")]


def test_slugify():
    assert slugify("[1hr Talk] Intro to Large Language Models") == "1hr-talk-intro-to-large-language-models"
    assert slugify("!!!") == "video"
