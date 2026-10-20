"""Turn a transcript into structured study notes with Claude."""

from __future__ import annotations

import sys

from .youtube import Segment, VideoInfo, fmt_ts

MODEL = "claude-opus-5-5"

NOTES_SYSTEM_PROMPT = """You are an expert note-taker who turns video transcripts into notes a \
diligent student would be proud of: accurate, well organized, and easy to review later.

Write the notes in Markdown with this structure:

1. `# <Video title>` followed by a one-line metadata line (channel, duration, link).
2. `## TL;DR` - 2-4 sentences capturing the core message.
3. `## Key Takeaways` - the 5-10 most important ideas as bullets, each one a complete thought.
4. `## Detailed Notes` - organized by topic (use the video's chapters when given, otherwise infer \
sections from the content). Use `###` headings, bullets, and nested bullets. Preserve concrete \
details: numbers, names, definitions, steps, examples, code, formulas, and arguments. Start each \
section heading with its start timestamp as a link, like `### [12:34](URL&t=754s) Section name`.
5. `## Definitions & Concepts` - a table of important terms and their meaning (omit if none).
6. `## Action Items / How to Apply` - practical steps the viewer can take (omit if not applicable).
7. `## Questions for Review` - 3-6 questions that test understanding, with short answers in a \
collapsible `<details>` block.

Rules:
- Stay faithful to the transcript. Do not invent facts; if the speaker is unclear or the \
transcript looks garbled, say so briefly rather than guessing.
- Auto-generated captions contain recognition errors; silently fix obvious mis-hearings of \
names and technical terms when context makes the intended word clear.
- Write in your own words rather than copying long stretches of the transcript; short quotes \
are fine when wording matters.
- Write the notes in the language requested by the user message.
- Output only the Markdown notes, with no preamble."""


def generate_notes(info: VideoInfo, paragraphs: list[Segment], notes_language: str, effort: str) -> str:
    import anthropic

    timed = "\n".join(f"[{fmt_ts(p.start)} | {int(p.start)}s] {p.text}" for p in paragraphs)
    chapters = "\n".join(f"- {fmt_ts(c['start_time'])} {c.get('title', '')}" for c in info.chapters) or "(none)"
    user_msg = (
        f"Video title: {info.title}\n"
        f"Channel: {info.channel or 'unknown'}\n"
        f"Duration: {fmt_ts(info.duration) if info.duration else 'unknown'}\n"
        f"URL (append &t=<seconds>s for timestamp links): {info.url}\n"
        f"Chapters:\n{chapters}\n\n"
        f"Description:\n<description>\n{info.description or '(none)'}\n</description>\n\n"
        f"Transcript (each line is [mm:ss | seconds] text):\n<transcript>\n{timed}\n</transcript>\n\n"
        f"Write the notes in {notes_language}."
    )

    client = anthropic.Anthropic()
    print(f"Generating notes with {MODEL} (effort={effort})...", file=sys.stderr)
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=64000,
        system=NOTES_SYSTEM_PROMPT,
        thinking={"type": "adaptive"},
        output_config={"effort": effort},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        messages=[{"role": "user", "content": user_msg}],
    ) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise RuntimeError("The model declined to summarize this video.")
    notes = "".join(b.text for b in message.content if b.type == "text").strip()
    if message.stop_reason == "max_tokens":
        notes += "\n\n> ⚠️ Notes were cut off because they hit the output length limit."
    return notes
