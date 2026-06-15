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


def record_feedback(state: dict, datum: str, edition: str, rating: str, chat_id: str) -> None:
    """Hält eine Ein-Tap-Relevanzbewertung fest (rating: 'up' oder 'down')."""
    now = datetime.now(timezone.utc)
    feedback = state.setdefault("feedback", [])
    feedback.append({
        "date": datum,
        "edition": edition,
        "rating": rating,
        "chat_id": chat_id,
        "ts": now.isoformat(),
    })
    # Nur die letzten 30 Tage behalten (Muster wie record_stats).
    cutoff = now.date().toordinal() - 30
    state["feedback"] = [
        f for f in feedback
        if datetime.fromisoformat(f["date"]).toordinal() >= cutoff
    ]


def feedback_summary(state: dict, cutoff_date: str) -> dict:
    """Zählt 👍/👎 ab cutoff_date (ISO-Datum). Letzte Bewertung pro Ausgabe zählt."""
    latest: dict[tuple[str, str], str] = {}
    for f in state.get("feedback", []):
        if f["date"] >= cutoff_date:
            latest[(f["date"], f["edition"])] = f["rating"]
    up = sum(1 for r in latest.values() if r == "up")
    down = sum(1 for r in latest.values() if r == "down")
    return {"up": up, "down": down, "total": up + down}


def _strip_markdown(text: str) -> str:
    """Macht aus einer Delta-Zeile einen sauberen Verlauf-Eintrag (reiner Text)."""
    import re
    text = re.sub(r"\s*\[[^\]]*\]\([^)]*\)", "", text)      # Links ganz weg (inkl. → Artikel)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)          # **bold**
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", text)  # *kursiv*
    text = text.lstrip("-• ").strip()
    # Führende Label-Präfixe wegkürzen ("EZB:", "Seit deinem letzten Stand:") —
    # höchstens zwei, damit kein echter Satzinhalt verloren geht.
    for _ in range(2):
        m = re.match(r"^[^.!?]{1,35}:\s+", text)
        if not m:
            break
        text = text[m.end():]
    return text.strip()


def update_dossier(state: dict, lagebild_md: str, topics: list, datum: str) -> None:
    """Hält die heutige Themen-Entwicklung je Tracker als Verlauf fest.

    Liest den Abschnitt „## Deine Themen" der erzeugten Ausgabe und ordnet jede
    Delta-Zeile per Schlagwort einem Tracker zu. Der Abschnitt erscheint laut
    Prompt nur bei materieller Änderung — also genau dann, wenn ein Eintrag fällt.
    """
    from .synthesize import topic_keyword, topic_name

    lines = lagebild_md.splitlines()
    section: list[str] = []
    in_section = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("## "):
            if in_section:
                break  # nächste Überschrift beendet den Abschnitt
            in_section = "Deine Themen" in line
            continue
        if in_section:
            if line.startswith("---"):
                break
            if line:
                section.append(line)
    if not section:
        return

    dossier = state.setdefault("dossier", {})
    for line in section:
        clean = _strip_markdown(line)
        if not clean:
            continue
        for topic in topics:
            kw = topic_keyword(topic)
            # Gegen die Originalzeile matchen — das Schlagwort kann im (später
            # entfernten) Label-Präfix „**Miet:**" stehen, nicht im Satzkörper.
            if kw and kw.lower() in line.lower():
                name = topic_name(topic)
                entries = dossier.setdefault(name, [])
                entries.append({"date": datum, "summary": clean})
                # Pro Thema: letzte 5 Einträge / 30 Tage behalten.
                cutoff = datetime.now(timezone.utc).date().toordinal() - 30
                dossier[name] = [
                    e for e in entries
                    if datetime.fromisoformat(e["date"]).toordinal() >= cutoff
                ][-5:]
                break  # eine Zeile zählt nur zum ersten passenden Thema


def record_article_feedback(
    state: dict, datum: str, edition: str, article_idx: int, rating: str, chat_id: str
) -> None:
    """Hält Artikel-Relevanz-Bewertung fest (rating: 'up' oder 'down')."""
    now = datetime.now(timezone.utc)
    entries = state.setdefault("article_feedback", [])
    entries.append({
        "date": datum,
        "edition": edition,
        "article_idx": article_idx,
        "rating": rating,
        "chat_id": chat_id,
        "ts": now.isoformat(),
    })
    cutoff = now.date().toordinal() - 30
    state["article_feedback"] = [
        e for e in entries
        if datetime.fromisoformat(e["date"]).toordinal() >= cutoff
    ]


def article_feedback_hint(state: dict, cutoff_date: str) -> str:
    """Kalibrierungshinweis aus Artikel-Bewertungen für den Synthese-Prompt."""
    entries = [
        e for e in state.get("article_feedback", [])
        if e.get("date", "") >= cutoff_date
    ]
    if len(entries) < 3:
        return ""
    up = sum(1 for e in entries if e["rating"] == "up")
    down = len(entries) - up
    if down / len(entries) > 0.5:
        return (
            f"⚠️ Artikel-Feedback: {down}/{len(entries)} Artikel wurden als "
            "nicht relevant markiert — schärfere Themenauswahl, weniger Randthemen.\n"
        )
    if up / len(entries) > 0.7:
        return (
            f"✅ Artikel-Feedback: {up}/{len(entries)} Artikel als relevant bewertet — "
            "Kurs halten.\n"
        )
    return ""


def save_user_topic_prefs(state: dict, topic_names: list[str]) -> None:
    """Speichert vom Nutzer gewählte Themen-Präferenzen (via App-Assessment oder Telegram)."""
    state["user_topic_prefs"] = topic_names


def save_topic_articles(state: dict, topics: list, articles: list) -> None:
    """Speichert bis zu 3 themenrelevante Artikel pro Topic in state für die Web-App."""
    from .synthesize import topic_keyword, topic_name as _tn
    result: dict[str, list[dict]] = {}
    for topic in topics:
        name = _tn(topic)
        kw = topic_keyword(topic).lower()
        if not kw:
            continue
        matched = sorted(
            [a for a in articles if kw in a.title.lower() or kw in (a.teaser or "").lower()],
            key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
        result[name] = [
            {
                "title": a.title,
                "link": a.link,
                "date": a.published.strftime("%Y-%m-%d") if a.published else "",
            }
            for a in matched[:3]
        ]
    state["topic_articles"] = result


def current_streak(state: dict) -> int:
    """Aufeinanderfolgende Kalendertage (bis heute) mit mindestens einer Ausgabe."""
    from datetime import date, timedelta
    days = {s["date"] for s in state.get("stats", [])}
    if not days:
        return 0
    d, streak = date.today(), 0
    if d.isoformat() not in days:  # heute noch keine Ausgabe → ab gestern zählen
        d -= timedelta(days=1)
    while d.isoformat() in days:
        streak += 1
        d -= timedelta(days=1)
    return streak


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
