"""Load settings such as ANTHROPIC_API_KEY from a .env file, so the key doesn't
have to be exported in every terminal."""

from __future__ import annotations

import os
from pathlib import Path

# The current folder first, then the project root (for `pip install -e .` checkouts).
_CANDIDATES = (Path.cwd() / ".env", Path(__file__).resolve().parents[2] / ".env")


def load_env() -> None:
    """Set variables from the first .env found; values already in the environment win."""
    for path in _CANDIDATES:
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.removeprefix("export ").split("=", 1)
            key, value = key.strip(), value.strip().strip("'\"")
            if key and value and not os.environ.get(key):
                os.environ[key] = value
        return
