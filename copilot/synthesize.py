"""Erzeugt das Lagebild: Prompt zusammenbauen, Claude API aufrufen."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from . import i18n

BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"
MANUAL_DIR = BASE_DIR / "manual_input"


def topic_name(topic) -> str:
    """Name eines Trackers — akzeptiert String oder {name, schlagwort}."""
    return topic["name"] if isinstance(topic, dict) else str(topic)


def topic_keyword(topic) -> str:
    """Schlagwort zum Zuordnen einer Delta-Zeile; Fallback: erstes Wort des Namens."""
    if isinstance(topic, dict) and topic.get("schlagwort"):
        return str(topic["schlagwort"])
    return topic_name(topic).split()[0] if topic_name(topic) else ""


def date_label(edition_label: str, lang: str = "de") -> str:
    now = datetime.now()
    return i18n.t(lang, "date_label_fmt").format(
        weekday=i18n.t(lang, "weekdays")[now.weekday()],
        day=now.day,
        month=i18n.t(lang, "months")[now.month - 1],
        year=now.year,
        edition=edition_label,
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
    next_edition: str = "",
    edition_emoji: str = "☀️",
    show_vorausschau: bool = False,
    lang: str = "de",
    prompt_file: str = "lagebild.md",
    wiki_stands: dict[str, str] | None = None,
) -> str:
    from .vorausschau import format_vorausschau

    template = (PROMPTS_DIR / prompt_file).read_text(encoding="utf-8")
    tracker_hint = i18n.t(lang, "tracker_hint") if topics else ""
    vorausschau = format_vorausschau(termine or [], lang) if show_vorausschau else ""
    template = (
        template.replace("{EDITION_EMOJI}", edition_emoji)
        .replace("{DATUM_LABEL}", date_label(edition_label, lang))
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
        lines.append(i18n.t(lang, "section_topics"))
        for topic in topics:
            name = topic_name(topic)
            lines.append(f"- {name}")
            # Themen-Wiki hat Vorrang: der kurze „## Stand"-Kopf (first-hand aus den
            # Quell-Artikeln) ersetzt den second-hand Dossier-Verlauf, wenn vorhanden.
            stand = (wiki_stands or {}).get(name)
            if stand:
                for sline in stand.splitlines():
                    if sline.strip():
                        lines.append(f"{i18n.t(lang, 'wiki_stand_prefix')}{sline.strip()}")
            else:
                verlauf = _format_verlauf(dossier.get(name, []))
                if verlauf:
                    lines.append(f"{i18n.t(lang, 'verlauf_prefix')}{verlauf}")
        lines.append("")

    fulltexts = load_manual_fulltexts()
    if fulltexts:
        lines.append(i18n.t(lang, "section_fulltexts"))
        for title, text in fulltexts:
            lines.append(f"### {title}\n{text}\n")

    lines.append(i18n.t(lang, "section_articles_fmt").format(n=len(articles)))
    for article in articles:
        published = (
            article.published.strftime("%d.%m. %H:%M UTC") if article.published else "ohne Datum"
        )
        link_part = f"\n  Link: {article.link}" if article.link else ""
        author_part = (
            f"{i18n.t(lang, 'author_prefix')}{article.author}"
            if getattr(article, "author", None)
            else ""
        )
        if article.fulltext:
            lines.append(
                f"- [{article.ressort}] {article.title} ({published}){author_part}{link_part}\n"
                f"  [VOLLTEXT]\n{article.fulltext}\n  [/VOLLTEXT]"
            )
        else:
            lines.append(
                f"- [{article.ressort}] {article.title} ({published}){author_part}\n  {article.teaser}{link_part}"
            )

    return "\n".join(lines)


def generate_assessment_questions(articles: list, topics: list, config: dict) -> list[dict]:
    """Generiert je Thema eine konkrete, artikel-basierte Assessment-Frage via Claude."""
    import json as _json
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or not articles or not topics:
        return []
    import anthropic
    topic_lines = "\n".join(
        f"- {topic_name(t)} (Schlagwort: {topic_keyword(t)})" for t in topics
    )
    article_lines = "\n".join(
        f"- [{a.ressort}] {a.title}: {(a.teaser or '')[:100]}"
        for a in articles[:30]
    )
    if (config.get("language") or "de") == "en":
        prompt = (
            "You generate assessment questions for a news app.\n\n"
            f"Available topics:\n{topic_lines}\n\n"
            f"Current articles (today):\n{article_lines}\n\n"
            "Task: Generate exactly one assessment question for EACH topic.\n"
            "Each question should:\n"
            "- Refer concretely to current articles where possible\n"
            "- Be phrased personally (\"affects you\", \"interests you\")\n"
            "- Be short (1 sentence, max. 120 characters)\n"
            "- Be answerable with yes or no\n\n"
            "Reply ONLY with a JSON array:\n"
            '[{"name": "<exact topic name>", "question": "<question>"}]\n'
            "No other output."
        )
    else:
        prompt = (
            "Du generierst Assessment-Fragen für eine Nachrichten-App.\n\n"
            f"Verfügbare Themen:\n{topic_lines}\n\n"
            f"Aktuelle Presse-Artikel (heute):\n{article_lines}\n\n"
            "Aufgabe: Generiere für JEDES Thema exakt eine Assessment-Frage.\n"
            "Die Frage soll:\n"
            "- Konkret auf aktuelle Artikel Bezug nehmen, wenn möglich\n"
            "- Persönlich formuliert sein (\"betrifft dich\", \"interessiert dich\")\n"
            "- Kurz sein (1 Satz, max. 120 Zeichen)\n"
            "- Mit Ja oder Nein beantwortbar sein\n\n"
            "Antworte NUR mit einem JSON-Array:\n"
            '[{"name": "<exakter Themenname>", "question": "<Frage>"}]\n'
            "Keine anderen Ausgaben."
        )
    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        m = re.search(r"\[.*\]", text, re.DOTALL)
        return _json.loads(m.group()) if m else []
    except Exception as exc:
        print(f"generate_assessment_questions Fehler: {exc}")
        return []


def assess_quality(lagebild: str, articles: list, config: dict) -> dict | None:
    """Bewertet ein fertiges Lagebild per LLM-as-Judge auf die Produktregeln.

    Idee angelehnt an das „Sample-Alignment"-Signal aus Proxy-KD (Chen et al.,
    2024): nicht das Modell wird destilliert, aber wir messen, wie gut das
    erzeugte Lagebild zum Qualitäts-Gate „passt". Ein zweiter, günstiger Claude-
    Call (Haiku) vergibt 1–5 je Dimension. Reines Beobachtungs-/Kalibrier-Signal:
    Es blockiert den Versand NIE und greift nicht ins Lagebild ein.

    Dimensionen (genau die CLAUDE.md-Produktregeln):
      - wesentlichkeit: nur Wesentliches, keine erzwungenen Füll-Punkte
      - delta:          klar „Was ist neu seit deinem letzten Stand"
      - kuerze:         Time-to-Informed kurz, kein Scroll-Anreiz
      - faktentreue:    durch das gelieferte Material gedeckt, nichts erfunden

    Rückgabe: dict mit Scores, Gesamtschnitt, gate_ok (Schwelle) und kurzem
    Verdikt — oder None, wenn kein API-Key gesetzt ist (z. B. Dry-Run).
    """
    import json as _json

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or not lagebild.strip():
        return None
    import anthropic

    material = "\n".join(
        f"- [{a.ressort}] {a.title}: {(a.teaser or '')[:160]}"
        for a in articles[:40]
    )
    lang = config.get("language") or "de"
    if lang == "en":
        prompt = (
            "You are a strict editorial quality judge for a news briefing product.\n"
            "The product optimizes for TIME-TO-INFORMED, never time-on-site. Rules:\n"
            "rather 1 honest point than 3 forced ones; clearly state what is NEW; "
            "stay short; never invent anything beyond the source material.\n\n"
            f"Source material the briefing was built from:\n{material}\n\n"
            f"The produced briefing:\n---\n{lagebild}\n---\n\n"
            "Rate each dimension from 1 (poor) to 5 (excellent):\n"
            "- essential: only what matters, no padded/forced filler points\n"
            "- delta: clearly conveys what is new since the last edition\n"
            "- brevity: short, no scroll-bait, respects time-to-informed\n"
            "- faithfulness: fully grounded in the material, nothing fabricated\n\n"
            "Reply ONLY with JSON, no other text:\n"
            '{"essential": <1-5>, "delta": <1-5>, "brevity": <1-5>, '
            '"faithfulness": <1-5>, "verdict": "<one short sentence>"}'
        )
        keymap = {
            "essential": "wesentlichkeit",
            "delta": "delta",
            "brevity": "kuerze",
            "faithfulness": "faktentreue",
        }
    else:
        prompt = (
            "Du bist eine strenge redaktionelle Qualitäts-Jury für ein Nachrichten-"
            "Lagebild. Das Produkt optimiert auf TIME-TO-INFORMED, nie auf Time-on-"
            "Site. Regeln: lieber 1 ehrlicher Punkt als 3 erzwungene; klar sagen, "
            "was NEU ist; kurz bleiben; nichts über das Quellmaterial hinaus "
            "erfinden.\n\n"
            f"Quellmaterial, aus dem das Lagebild gebaut wurde:\n{material}\n\n"
            f"Das erzeugte Lagebild:\n---\n{lagebild}\n---\n\n"
            "Bewerte jede Dimension von 1 (schlecht) bis 5 (ausgezeichnet):\n"
            "- wesentlichkeit: nur Wesentliches, keine erzwungenen Füll-Punkte\n"
            "- delta: macht klar, was seit der letzten Ausgabe neu ist\n"
            "- kuerze: kurz, kein Scroll-Anreiz, respektiert Time-to-Informed\n"
            "- faktentreue: vollständig durch das Material gedeckt, nichts erfunden\n\n"
            "Antworte NUR mit JSON, kein anderer Text:\n"
            '{"wesentlichkeit": <1-5>, "delta": <1-5>, "kuerze": <1-5>, '
            '"faktentreue": <1-5>, "verdikt": "<ein kurzer Satz>"}'
        )
        keymap = {k: k for k in ("wesentlichkeit", "delta", "kuerze", "faktentreue")}

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=config.get("judge_model", "claude-haiku-4-5-20251001"),
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        raw = _json.loads(m.group())
    except Exception as exc:
        print(f"assess_quality Fehler: {exc}")
        return None

    dims: dict[str, int] = {}
    for src, dst in keymap.items():
        try:
            dims[dst] = max(1, min(5, int(round(float(raw.get(src, 0))))))
        except (TypeError, ValueError):
            continue
    if not dims:
        return None
    gesamt = round(sum(dims.values()) / len(dims), 2)
    threshold = float(config.get("quality_gate_threshold", 3.5))
    result = dict(dims)
    result["gesamt"] = gesamt
    result["gate_ok"] = gesamt >= threshold
    verdikt = raw.get("verdikt") or raw.get("verdict") or ""
    if verdikt:
        result["verdikt"] = str(verdikt).strip()[:300]
    return result


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
