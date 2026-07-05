"""Merkt sich gesehene Artikel, damit die Abend-Ausgabe nur das Delta zeigt."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_PATH = BASE_DIR / "data" / "state.json"
MAX_SEEN = 2000  # alte Eintraege werden abgeschnitten


def set_state_path(path: str | None) -> None:
    """Setzt den State-Pfad (z. B. data/state.nyt.json für eine parallele Edition).

    None lässt den Default (data/state.json). Relative Pfade werden auf das
    Projekt-Wurzelverzeichnis bezogen, damit NYT- und Presse-Lauf getrennte
    „seen"-/Dossier-Stände führen und sich nicht überschreiben.
    """
    global STATE_PATH
    if not path:
        return
    p = Path(path)
    STATE_PATH = p if p.is_absolute() else BASE_DIR / p


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


def save_edition_points(state: dict, datum: str, edition: str, headings: list[str]) -> None:
    """Merkt sich die Punkt-Titel einer Ausgabe, damit 👍/👎-Taps (die nur einen
    Index tragen) später inhaltlich auflösbar sind."""
    if not headings:
        return
    points = state.setdefault("edition_points", {})
    points[f"{datum}|{edition}"] = headings
    # Nur die letzten 30 Tage behalten (Schlüsselformat: "YYYY-MM-DD|edition").
    cutoff = datetime.now(timezone.utc).date().toordinal() - 30
    state["edition_points"] = {
        k: v for k, v in points.items()
        if datetime.fromisoformat(k.split("|")[0]).toordinal() >= cutoff
    }


def record_article_feedback(
    state: dict, datum: str, edition: str, article_idx: int, rating: str, chat_id: str
) -> None:
    """Hält Artikel-Relevanz-Bewertung fest (rating: 'up' oder 'down')."""
    now = datetime.now(timezone.utc)
    headings = state.get("edition_points", {}).get(f"{datum}|{edition}", [])
    heading = headings[article_idx] if 0 <= article_idx < len(headings) else ""
    entries = state.setdefault("article_feedback", [])
    entries.append({
        "date": datum,
        "edition": edition,
        "article_idx": article_idx,
        "heading": heading,
        "rating": rating,
        "chat_id": chat_id,
        "ts": now.isoformat(),
    })
    cutoff = now.date().toordinal() - 30
    state["article_feedback"] = [
        e for e in entries
        if datetime.fromisoformat(e["date"]).toordinal() >= cutoff
    ]


def _feedback_headings(entries: list[dict], rating: str, limit: int = 5) -> list[str]:
    """Jüngste eindeutige Punkt-Titel mit der gegebenen Bewertung."""
    result: list[str] = []
    for e in reversed(entries):  # neueste zuerst
        h = e.get("heading", "").strip()
        if e["rating"] == rating and h and h not in result:
            result.append(h)
            if len(result) >= limit:
                break
    return result


def article_feedback_hint(state: dict, cutoff_date: str) -> str:
    """Kalibrierungshinweis aus Artikel-Bewertungen für den Synthese-Prompt.

    Bewusst KEINE Klick-Personalisierung: Der Hinweis kalibriert nur die
    Materialitäts-Schwelle des Auswahlprinzips („strenger prüfen"), er filtert
    keine Themen weg.
    """
    entries = [
        e for e in state.get("article_feedback", [])
        if e.get("date", "") >= cutoff_date
    ]
    if len(entries) < 3:
        return ""
    up = sum(1 for e in entries if e["rating"] == "up")
    down = len(entries) - up
    lines: list[str] = []
    if down / len(entries) > 0.5:
        lines.append(
            f"⚠️ Artikel-Feedback: {down}/{len(entries)} Artikel wurden als "
            "nicht relevant markiert — schärfere Themenauswahl, weniger Randthemen."
        )
    elif up / len(entries) > 0.7:
        lines.append(
            f"✅ Artikel-Feedback: {up}/{len(entries)} Artikel als relevant bewertet — "
            "Kurs halten."
        )
    downs = _feedback_headings(entries, "down")
    if downs:
        titel = " · ".join(f"„{h}“" for h in downs)
        lines.append(
            f"Als nicht relevant markiert wurden zuletzt: {titel} — "
            "vergleichbare Themen strenger an der Materialitäts-Schwelle prüfen."
        )
    ups = _feedback_headings(entries, "up")
    if ups:
        titel = " · ".join(f"„{h}“" for h in ups)
        lines.append(
            f"Als relevant markiert wurden zuletzt: {titel} — "
            "vergleichbare Entwicklungen bei gleicher Materialität priorisieren."
        )
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


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


def add_push_subscription(state: dict, sub: dict) -> None:
    """Speichert eine Web-Push-Subscription (dedupliziert per Endpoint)."""
    endpoint = sub.get("endpoint")
    if not endpoint:
        return
    subs = state.setdefault("push_subscriptions", [])
    if not any(s.get("endpoint") == endpoint for s in subs):
        subs.append(sub)


def remove_push_subscription(state: dict, endpoint: str) -> None:
    """Entfernt eine abgemeldete/abgelaufene Subscription."""
    subs = state.get("push_subscriptions", [])
    state["push_subscriptions"] = [s for s in subs if s.get("endpoint") != endpoint]


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
