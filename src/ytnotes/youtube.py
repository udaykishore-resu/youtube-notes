"""Fetch YouTube video metadata and transcripts."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse


@dataclass
class Segment:
    start: float
    text: str


@dataclass
class VideoInfo:
    video_id: str
    url: str
    title: str = "Untitled video"
    channel: str = ""
    duration: int = 0
    description: str = ""
    chapters: list[dict] = field(default_factory=list)


def extract_video_id(url: str) -> str:
    """Accept watch, youtu.be, shorts, embed, live URLs, or a bare 11-char id."""
    url = url.strip()
    if re.fullmatch(r"[\w-]{11}", url):
        return url
    parsed = urlparse(url if "://" in url else "https://" + url)
    host = (parsed.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
        qs = parse_qs(parsed.query)
        if "v" in qs:
            candidate = qs["v"][0]
        else:
            parts = [p for p in parsed.path.split("/") if p]
            candidate = parts[1] if len(parts) >= 2 and parts[0] in {"shorts", "embed", "live", "v"} else ""
    else:
        candidate = ""
    if not re.fullmatch(r"[\w-]{11}", candidate):
        raise ValueError(f"Could not find a YouTube video id in: {url}")
    return candidate


def fmt_ts(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def fetch_metadata(video_id: str) -> VideoInfo:
    url = f"https://www.youtube.com/watch?v={video_id}"
    info = VideoInfo(video_id=video_id, url=url)
    try:
        import yt_dlp

        with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
            data = ydl.extract_info(url, download=False)
        info.title = data.get("title") or info.title
        info.channel = data.get("channel") or data.get("uploader") or ""
        info.duration = int(data.get("duration") or 0)
        info.description = (data.get("description") or "")[:3000]
        info.chapters = data.get("chapters") or []
    except Exception as exc:  # metadata is nice-to-have; the transcript is what matters
        print(f"warning: could not fetch video metadata ({exc.__class__.__name__}); continuing", file=sys.stderr)
    return info


def fetch_transcript(video_id: str, languages: list[str]) -> tuple[list[Segment], str]:
    """Return (segments, language label). Prefers manual captions, then auto-generated,
    then any available language (translated to the first preferred language if possible)."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import CouldNotRetrieveTranscript

    api = YouTubeTranscriptApi()
    try:
        transcripts = api.list(video_id)
    except CouldNotRetrieveTranscript as exc:
        raise RuntimeError(f"No transcript available for this video: {exc.__class__.__name__}") from exc

    chosen = None
    for finder in (transcripts.find_manually_created_transcript, transcripts.find_generated_transcript):
        try:
            chosen = finder(languages)
            break
        except CouldNotRetrieveTranscript:
            continue
    if chosen is None:
        available = list(transcripts)
        if not available:
            raise RuntimeError("This video has no captions at all.")
        chosen = available[0]
        if chosen.is_translatable and any(t.language_code == languages[0] for t in chosen.translation_languages):
            chosen = chosen.translate(languages[0])

    fetched = chosen.fetch()
    segments = [Segment(s.start, s.text.replace("\n", " ").strip()) for s in fetched if s.text.strip()]
    label = chosen.language if chosen.is_generated else f"{chosen.language} (manual)"
    return segments, label


def group_segments(segments: list[Segment], window: float = 30.0) -> list[Segment]:
    """Merge caption fragments into ~30s paragraphs so the transcript reads naturally."""
    grouped: list[Segment] = []
    for seg in segments:
        if grouped and seg.start - grouped[-1].start < window:
            grouped[-1].text += " " + seg.text
        else:
            grouped.append(Segment(seg.start, seg.text))
    return grouped


def render_transcript(info: VideoInfo, paragraphs: list[Segment], lang_label: str) -> str:
    lines = [f"# Transcript: {info.title}", ""]
    meta = [f"[Watch on YouTube]({info.url})", f"Captions: {lang_label}"]
    if info.channel:
        meta.insert(0, f"Channel: {info.channel}")
    lines += [" · ".join(meta), ""]
    for p in paragraphs:
        lines.append(f"**[{fmt_ts(p.start)}]({info.url}&t={int(p.start)}s)** {p.text}")
        lines.append("")
    return "\n".join(lines)
