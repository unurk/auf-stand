"""Schreibt Analysen als Markdown in out/."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "out"


def write(text: str, mode: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    path = OUT_DIR / f"{ts}-{mode}.md"
    path.write_text(text, encoding="utf-8")
    return path
