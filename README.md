# ytnotes

Paste a YouTube link and get back either:

- **the transcript**: the full transcript in ~30-second paragraphs. Each paragraph has a clickable timestamp that jumps to that moment in the video.
- **study notes**: notes written by Claude (`claude-opus-5-5`), with a TL;DR, key takeaways, detailed notes by section (with timestamp links), a definitions table, action items, and review questions.

You can use it as a web app in your browser or as a command-line tool.

## Requirements

- Python 3.10 or newer (`python3 --version`)
- An Anthropic API key, needed only for notes. Get one at https://console.anthropic.com/settings/keys. Getting transcripts works without a key.

## Quick start

**1. Get the code**

```bash
git clone https://github.com/udaykishore-resu/youtube-notes.git
cd youtube-notes
```

**2. Create a virtual environment and install**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows, activate it with `.venv\Scripts\activate` instead.

**3. Add your API key**

```bash
cp .env.example .env
```

Open `.env` and paste your key after the `=`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

> ⚠️ Put the key in `.env`, never in `.env.example`. `.env` is gitignored. `.env.example` is committed, and GitHub will block a push that contains a key.

**4. Run the app**

```bash
ytnotes-web
```

This starts the app at http://127.0.0.1:8765 and opens it in your browser. Leave the terminal open: the app only runs while this command is running. Press **Ctrl+C** in that terminal to stop it.

## Using the web app

1. Paste a YouTube link into the box.
2. Click a button:
   - **Transcript**: shows the full transcript with clickable timestamps and a search box.
   - **Summarize** (or press Enter): Claude writes the notes, and they appear on the page as they're generated. A long video can take a minute or two.
3. Use **Copy** or **Download .md** to keep the result.

**Options** (under the link box):

| Option | Meaning |
|---|---|
| Caption languages | Languages to try, in order, e.g. `en hi`. If none match, it uses whatever captions exist, translated when possible. |
| Write notes in | The language for the notes, e.g. `Hindi`. |
| Thinking effort | Low is fastest and cheapest. Max is most thorough. High is the default. |

It accepts `watch?v=`, `youtu.be/`, `shorts/`, `embed/` and `live/` links, or a bare video id.

### Running it again later

Each time you open a new terminal:

```bash
cd youtube-notes
source .venv/bin/activate
ytnotes-web
```

To skip activating the environment, run `.venv/bin/ytnotes-web` from the project folder.

| Flag | Meaning |
|---|---|
| `--port 9000` | Use a different port (default `8765`). |
| `--no-browser` | Don't open a browser tab automatically. |
| `--host 0.0.0.0` | Make it reachable from other devices on your network. The default only allows access from this computer. |

## Command line

Instead of the web app, you can save the files directly:

```bash
ytnotes "https://www.youtube.com/watch?v=zjkBMFhNj_g"
```

This writes `transcript.md`, `transcript.txt` and `notes.md` to `output/<video-title>-<id>/`.

| Option | Meaning |
|---|---|
| `--lang en hi` | Caption languages to try, in order (default `en`). |
| `--notes-language Hindi` | Language the notes are written in (default English). |
| `--effort low…max` | How deeply the model thinks (default `high`). |
| `--out DIR` | Output folder (default `./output`). |
| `--transcript-only` | Skip the notes step. No API key needed. |

## Troubleshooting

| Problem | Fix |
|---|---|
| Browser says **"127.0.0.1 refused to connect"** | The app isn't running. Start `ytnotes-web` again and keep that terminal open. |
| **"Anthropic API key is missing"** | Put your key in `.env` (step 3), then click Summarize again. No restart is needed. |
| **"Address already in use"** when starting | The app is already running in another terminal. Use that one, stop it with Ctrl+C, or start with `--port 9000`. |
| **`command not found: ytnotes-web`** | Activate the environment first (`source .venv/bin/activate`), or run `.venv/bin/ytnotes-web`. |
| **"No transcript available"** | The video has captions turned off. Only videos with captions (manual or auto-generated) work. |
| **`RequestBlocked`** | YouTube is rate-limiting your IP. Wait a while or switch networks. |

A 1-hour video typically costs well under a dollar in API usage at `high` effort. Use `low` or `medium` to spend less.

## Project layout

```
src/ytnotes/
  youtube.py   # URL parsing, metadata (yt-dlp), transcript fetching and formatting
  notes.py     # the Claude prompt and API call that write the notes
  server.py    # local web server behind the UI (`ytnotes-web`)
  web/         # the single-page UI
  cli.py       # command-line interface (also runnable as `python -m ytnotes`)
  env.py       # loads ANTHROPIC_API_KEY from .env
tests/         # pytest unit tests (no network needed)
```

Run the tests with `pytest`.
