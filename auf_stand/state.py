"""Merkt sich gesehene Artikel, damit die Abend-Ausgabe nur das Delta zeigt."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "state.json"
MAX_SEEN = 2000  # alte Eintraege werden abgeschnitten


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"seen": {}, "last_run": {}}


def save_state(state: dict) -> None:
    seen = state.get("seen", {})
    if len(seen) > MAX_SEEN:
        newest = sorted(seen.items(), key=lambda kv: kv[1], reverse=True)[:MAX_SEEN]
        state["seen"] = dict(newest)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def split_new(articles: list, state: dict) -> tuple[list, list]:
    """Teilt in (neu, bereits gesehen)."""
    seen = state.get("seen", {})
    new = [a for a in articles if a.id not in seen]
    old = [a for a in articles if a.id in seen]
    return new, old


def mark_seen(articles: list, state: dict, edition: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    seen = state.setdefault("seen", {})
    for article in articles:
        seen[article.id] = now
    state.setdefault("last_run", {})[edition] = now


def record_stats(state: dict, edition: str, points: int, words: int, new_articles: int) -> None:
    """Zeichnet pro Ausgabe Kennzahlen auf — Grundlage für die Wochen-Quittung."""
    now = datetime.now(timezone.utc)
    stats = state.setdefault("stats", [])
    stats.append({
        "date": now.date().isoformat(),
        "ts": now.isoformat(),
        "edition": edition,
        "points": points,
        "words": words,
        "new_articles": new_articles,
    })
    # Nur die letzten 30 Tage behalten
    cutoff = now.date().toordinal() - 30
    state["stats"] = [
        s for s in stats
        if datetime.fromisoformat(s["date"]).toordinal() >= cutoff
    ]
