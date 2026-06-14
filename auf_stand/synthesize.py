"""Erzeugt das Lagebild: Prompt zusammenbauen, Claude API aufrufen."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPT_PATH = BASE_DIR / "prompts" / "lagebild.md"
MANUAL_DIR = BASE_DIR / "manual_input"

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONTHS = [
    "Jänner", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


def topic_name(topic) -> str:
    """Name eines Trackers — akzeptiert String oder {name, schlagwort}."""
    return topic["name"] if isinstance(topic, dict) else str(topic)


def topic_keyword(topic) -> str:
    """Schlagwort zum Zuordnen einer Delta-Zeile; Fallback: erstes Wort des Namens."""
    if isinstance(topic, dict) and topic.get("schlagwort"):
        return str(topic["schlagwort"])
    return topic_name(topic).split()[0] if topic_name(topic) else ""


def date_label(edition_label: str) -> str:
    now = datetime.now()
    return (
        f"{WEEKDAYS[now.weekday()]}, {now.day}. {MONTHS[now.month - 1]} "
        f"{now.year} · {edition_label}"
    )


def load_manual_fulltexts() -> list[tuple[str, str]]:
    """Liest manuell abgelegte Volltexte: (Titel, Text)."""
    texts: list[tuple[str, str]] = []
    if not MANUAL_DIR.exists():
        return texts
    for path in sorted(MANUAL_DIR.glob("*.txt")) + sorted(MANUAL_DIR.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            continue
        first, _, rest = raw.partition("\n")
        texts.append((first.strip("# ").strip(), rest.strip()))
    return texts


def _format_verlauf(entries: list[dict]) -> str:
    """Kompakte Verlaufszeile aus den letzten Dossier-Einträgen."""
    parts = []
    for e in entries[-3:]:
        d = e.get("date", "")
        tag = f"[{d[8:10]}.{d[5:7]}.] " if len(d) >= 10 else ""
        parts.append(f"{tag}{e.get('summary', '')}")
    return " ".join(parts)


def build_prompt(
    articles: list,
    topics: list,
    edition_label: str,
    termine: list[dict] | None = None,
    dossier: dict | None = None,
    article_feedback_hint: str = "",
    user_topic_prefs: list[str] | None = None,
) -> str:
    from .vorausschau import format_vorausschau

    template = PROMPT_PATH.read_text(encoding="utf-8")
    tracker_hint = (
        "## Deine Themen\n[Nur falls es zu verfolgten Themen materielle "
        "Änderungen gibt — sonst Abschnitt weglassen]"
        if topics
        else ""
    )
    is_morning = "Morgen" in edition_label
    next_edition = "Nächstes Update: heute 16:00." if is_morning else "Nächste Ausgabe: morgen 7:00."
    vorausschau = format_vorausschau(termine or []) if is_morning else ""
    template = (
        template.replace("{DATUM_LABEL}", date_label(edition_label))
        .replace("{TRACKER_SECTION_HINT}", tracker_hint)
        .replace("{VORAUSSCHAU_SECTION}", vorausschau)
        .replace("{LESEZEIT}", "90")
        .replace("{NAECHSTE_AUSGABE}", next_edition)
    )

    lines = [template]
    if user_topic_prefs:
        pref_hint = (
            "\n\n---\n\n# Nutzerpräferenzen\n"
            f"Der Nutzer möchte bevorzugt über folgende Themen informiert werden: "
            f"{', '.join(user_topic_prefs)}.\n"
            "Priorisiere diese Themen im Lagebild, sofern es relevante Entwicklungen gibt.\n"
        )
        lines.append(pref_hint)
    if article_feedback_hint:
        lines.append(f"\n\n---\n\n# Kalibrierung\n{article_feedback_hint}")
    lines.append("\n\n---\n\n# Material\n")

    if topics:
        dossier = dossier or {}
        lines.append("## Verfolgte Themen\n")
        for topic in topics:
            name = topic_name(topic)
            lines.append(f"- {name}")
            verlauf = _format_verlauf(dossier.get(name, []))
            if verlauf:
                lines.append(f"  Verlauf: {verlauf}")
        lines.append("")

    fulltexts = load_manual_fulltexts()
    if fulltexts:
        lines.append("## Volltexte (haben Vorrang)\n")
        for title, text in fulltexts:
            lines.append(f"### {title}\n{text}\n")

    lines.append(f"## Artikel aus den RSS-Feeds ({len(articles)} Stück)\n")
    for article in articles:
        published = (
            article.published.strftime("%d.%m. %H:%M UTC") if article.published else "ohne Datum"
        )
        link_part = f"\n  Link: {article.link}" if article.link else ""
        if article.fulltext:
            lines.append(
                f"- [{article.ressort}] {article.title} ({published}){link_part}\n"
                f"  [VOLLTEXT]\n{article.fulltext}\n  [/VOLLTEXT]"
            )
        else:
            lines.append(
                f"- [{article.ressort}] {article.title} ({published})\n  {article.teaser}{link_part}"
            )

    return "\n".join(lines)


def synthesize(prompt: str, config: dict) -> str:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "ANTHROPIC_API_KEY fehlt. .env anlegen (siehe .env.example) "
            "oder mit --dry-run ohne API testen."
        )
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=config.get("model", "claude-sonnet-4-6"),
        max_tokens=int(config.get("max_tokens", 1500)),
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text").strip()
