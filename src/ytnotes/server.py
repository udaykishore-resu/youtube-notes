"""Local web UI: paste a YouTube link, then get the transcript or the notes.

Run with `ytnotes-web` (or `python -m ytnotes.server`), then open http://127.0.0.1:8765.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files

from .notes import MODEL, stream_notes
from .youtube import (
    Segment,
    VideoInfo,
    extract_video_id,
    fetch_metadata,
    fetch_transcript,
    group_segments,
    render_transcript,
)

EFFORTS = {"low", "medium", "high", "xhigh", "max"}

# video_id + languages -> (info, paragraphs, lang_label, plain_text), so clicking
# "Summarize" after "Transcript" doesn't hit YouTube twice.
_cache: dict[tuple, tuple[VideoInfo, list[Segment], str, str]] = {}
_cache_lock = threading.Lock()


def load_video(url: str, languages: list[str]) -> tuple[VideoInfo, list[Segment], str, str]:
    video_id = extract_video_id(url)
    key = (video_id, tuple(languages))
    with _cache_lock:
        if key in _cache:
            return _cache[key]
    info = fetch_metadata(video_id)
    segments, lang_label = fetch_transcript(video_id, languages)
    result = (info, group_segments(segments), lang_label, " ".join(s.text for s in segments))
    with _cache_lock:
        _cache[key] = result
    return result


def video_json(info: VideoInfo, lang_label: str) -> dict:
    return {
        "id": info.video_id,
        "url": info.url,
        "title": info.title,
        "channel": info.channel,
        "duration": info.duration,
        "captions": lang_label,
        "thumbnail": f"https://i.ytimg.com/vi/{info.video_id}/hqdefault.jpg",
    }


def parse_languages(raw) -> list[str]:
    if isinstance(raw, str):
        raw = raw.replace(",", " ").split()
    langs = [str(x).strip() for x in (raw or []) if str(x).strip()]
    return langs or ["en"]


class Handler(BaseHTTPRequestHandler):
    server_version = "ytnotes"

    def log_message(self, fmt, *args):  # keep the terminal quiet except for errors
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(fmt, *args)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = files("ytnotes").joinpath("web/index.html").read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            return self._json({"error": "Invalid request body."}, HTTPStatus.BAD_REQUEST)

        if self.path == "/api/transcript":
            self._transcript(payload)
        elif self.path == "/api/notes":
            self._notes(payload)
        else:
            self.send_error(HTTPStatus.NOT_FOUND)

    def _transcript(self, payload: dict):
        try:
            info, paragraphs, lang_label, plain = load_video(payload.get("url", ""), parse_languages(payload.get("lang")))
        except Exception as exc:
            return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        self._json({
            "video": video_json(info, lang_label),
            "paragraphs": [{"start": p.start, "text": p.text} for p in paragraphs],
            "markdown": render_transcript(info, paragraphs, lang_label),
            "text": plain,
        })

    def _notes(self, payload: dict):
        """Stream newline-delimited JSON events: video, delta*, then done or error."""
        effort = payload.get("effort", "high")
        if effort not in EFFORTS:
            effort = "high"
        notes_language = str(payload.get("notes_language") or "English")[:40]

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        def emit(event: dict):
            self.wfile.write((json.dumps(event) + "\n").encode())
            self.wfile.flush()

        try:
            info, paragraphs, lang_label, _ = load_video(payload.get("url", ""), parse_languages(payload.get("lang")))
            emit({"type": "video", "video": video_json(info, lang_label), "model": MODEL})
            for text in stream_notes(info, paragraphs, notes_language, effort):
                emit({"type": "delta", "text": text})
            emit({"type": "done"})
        except (BrokenPipeError, ConnectionResetError):
            pass  # the browser tab went away
        except Exception as exc:
            try:
                emit({"type": "error", "error": friendly_error(exc)})
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _json(self, data: dict, status: HTTPStatus = HTTPStatus.OK):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def friendly_error(exc: Exception) -> str:
    try:
        import anthropic

        if isinstance(exc, anthropic.AuthenticationError):
            return "Anthropic API key is missing or invalid. Set ANTHROPIC_API_KEY and restart ytnotes-web."
        if isinstance(exc, anthropic.RateLimitError):
            return "Rate limited by the Anthropic API. Wait a moment and try again."
        if isinstance(exc, anthropic.APIConnectionError):
            return "Could not reach the Anthropic API. Check your internet connection."
    except ImportError:
        pass
    if "api_key" in str(exc).lower() or "authentication" in str(exc).lower():
        return "Anthropic API key is missing. Set ANTHROPIC_API_KEY and restart ytnotes-web."
    return str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(prog="ytnotes-web", description="Local web UI for ytnotes")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}"
    print(f"ytnotes UI running at {url}  (Ctrl+C to stop)", file=sys.stderr)
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, [url]).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
