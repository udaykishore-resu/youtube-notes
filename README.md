# ytnotes

Paste a YouTube link and get back:

- **`transcript.md`**: the full transcript, grouped into ~30-second paragraphs. Each paragraph has a clickable timestamp that jumps to that moment in the video.
- **`transcript.txt`**: the same transcript as plain text.
- **`notes.md`**: structured study notes written by Claude (`claude-opus-5-5`). They contain a TL;DR, key takeaways, detailed notes by section (with timestamp links), a definitions table, action items, and review questions.

## Setup

```bash
cd youtube-notes
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export ANTHROPIC_API_KEY=sk-ant-...   # get one at https://console.anthropic.com
```

## Web UI

```bash
ytnotes-web
```

This opens http://127.0.0.1:8765 in your browser. Paste a YouTube link, then click:

- **Transcript**: shows the full transcript with clickable timestamps and a search box.
- **Summarize** (or press Enter): Claude writes the notes, and they appear on the page as they're generated.

Both views have **Copy** and **Download .md** buttons. Caption language, notes language and thinking effort are under **Options**. Use `ytnotes-web --port 9000` to change the port, or `--no-browser` to skip opening a tab.

## Command line

```bash
ytnotes "https://www.youtube.com/watch?v=zjkBMFhNj_g"
```

Output is saved to `output/<video-title>-<id>/`.

| Option | Meaning |
|---|---|
| `--lang en hi` | Caption languages to try, in order (default `en`). If none match, it falls back to any available captions, translated when possible. |
| `--notes-language Hindi` | Language the notes are written in (default English). |
| `--effort low…max` | How deeply the model thinks (default `high`). Higher effort gives better notes and costs more. |
| `--out DIR` | Output folder (default `./output`). |
| `--transcript-only` | Skip the AI step. No API key needed. |

It accepts `watch?v=`, `youtu.be/`, `shorts/`, `embed/`, `live/` links, or a bare video id.

## Notes

- It only works on videos that have captions (manual or auto-generated). Videos with captions turned off are not supported.
- If YouTube rate-limits your IP (`RequestBlocked`), wait a while or use a different network.
- A 1-hour video costs roughly $0.10–0.30 in API usage at `high` effort.

## Project layout

```
src/ytnotes/
  youtube.py   # URL parsing, metadata (yt-dlp), transcript fetching and formatting
  notes.py     # the Claude prompt and API call that write the notes
  cli.py       # command-line interface (also runnable as `python -m ytnotes`)
  server.py    # local web server behind the UI (`ytnotes-web`)
  web/         # the single-page UI
tests/         # pytest unit tests (no network needed)
```

Run the tests with `pytest`.
