"""Command-line entry point: ytnotes URL [options]."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from . import __version__
from .env import load_env
from .notes import generate_notes
from .youtube import extract_video_id, fetch_metadata, fetch_transcript, group_segments, render_transcript


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", slug)[:60] or "video"


def main() -> int:
    load_env()
    parser = argparse.ArgumentParser(prog="ytnotes", description="YouTube link -> transcript + perfect notes")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("url", help="YouTube URL or video id")
    parser.add_argument("--lang", nargs="+", default=["en"], help="preferred caption languages, in order (default: en)")
    parser.add_argument("--notes-language", default="English", help="language to write the notes in")
    parser.add_argument("--out", default="output", help="output directory (default: ./output)")
    parser.add_argument("--effort", default="high", choices=["low", "medium", "high", "xhigh", "max"],
                        help="how hard the model thinks (default: high)")
    parser.add_argument("--transcript-only", action="store_true", help="skip the AI notes step")
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
        print(f"Video id: {video_id}", file=sys.stderr)
        info = fetch_metadata(video_id)
        print(f"Title: {info.title}", file=sys.stderr)
        segments, lang_label = fetch_transcript(video_id, args.lang)
        paragraphs = group_segments(segments)
        print(f"Transcript: {len(segments)} caption lines, {lang_label}", file=sys.stderr)

        out_dir = Path(args.out) / f"{slugify(info.title)}-{video_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        transcript_path = out_dir / "transcript.md"
        transcript_path.write_text(render_transcript(info, paragraphs, lang_label), encoding="utf-8")
        (out_dir / "transcript.txt").write_text(" ".join(s.text for s in segments), encoding="utf-8")
        print(f"Saved {transcript_path}", file=sys.stderr)

        if not args.transcript_only:
            notes_path = out_dir / "notes.md"
            notes_path.write_text(generate_notes(info, paragraphs, args.notes_language, args.effort) + "\n",
                                  encoding="utf-8")
            print(f"Saved {notes_path}", file=sys.stderr)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
