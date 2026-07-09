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
    """Generiert je Thema eine konkrete, artikel-basierte Assessment-Frage."""
    import json as _json
    if not _provider_configured(config) or not articles or not topics:
        return []
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
        text = _complete(prompt, config, max_tokens=1000, anthropic_model="claude-haiku-4-5-20251001")
        m = re.search(r"\[.*\]", text, re.DOTALL)
        return _json.loads(m.group()) if m else []
    except Exception as exc:
        print(f"generate_assessment_questions Fehler: {exc}")
        return []


def synthesize(prompt: str, config: dict) -> str:
    """Erzeugt das Lagebild über den konfigurierten Provider (anthropic | glm)."""
    return _complete(prompt, config, max_tokens=int(config.get("max_tokens", 1500)))


# ---------------------------------------------------------------------------
# Provider-Abstraktion: anthropic (Claude, Default) oder glm (OpenRouter,
# OpenAI-kompatibel via httpx — kein zusätzliches SDK, CLAUDE.md-Konvention).
# ---------------------------------------------------------------------------

class _TransientError(Exception):
    """API-Fehler, bei dem sich ein Wiederholungsversuch lohnt (Rate-Limit/Überlast)."""


_RETRY_STATUS = {408, 429, 500, 502, 503, 529}


def _provider_configured(config: dict) -> bool:
    if config.get("provider", "anthropic") == "glm":
        return bool(os.environ.get("ZAI_API_KEY"))
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _complete(prompt: str, config: dict, max_tokens: int, anthropic_model: str | None = None) -> str:
    """Ein Prompt → Text. Transiente Fehler werden bis zu 2× mit Backoff wiederholt."""
    import time

    if config.get("provider", "anthropic") == "glm":
        call = lambda: _complete_glm(prompt, config, max_tokens)  # noqa: E731
    else:
        model = anthropic_model or config.get("model", "claude-sonnet-4-6")
        call = lambda: _complete_anthropic(prompt, model, max_tokens)  # noqa: E731

    for attempt in range(3):
        try:
            return call()
        except _TransientError as exc:
            if attempt == 2:
                raise RuntimeError(f"Synthese nach 3 Versuchen fehlgeschlagen: {exc}") from exc
            wait = 2 ** (attempt + 1)
            print(f"Synthese-Fehler (transient): {exc} — neuer Versuch in {wait}s.")
            time.sleep(wait)
    raise AssertionError("unreachable")


def _complete_anthropic(prompt: str, model: str, max_tokens: int) -> str:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit(
            "ANTHROPIC_API_KEY fehlt. .env anlegen (siehe .env.example) "
            "oder mit --dry-run ohne API testen."
        )
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIConnectionError as exc:
        raise _TransientError(str(exc)) from exc
    except anthropic.APIStatusError as exc:
        if exc.status_code in _RETRY_STATUS:
            raise _TransientError(f"HTTP {exc.status_code}") from exc
        raise
    return "".join(block.text for block in response.content if block.type == "text").strip()


def _complete_glm(prompt: str, config: dict, max_tokens: int) -> str:
    import httpx

    api_key = os.environ.get("ZAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "ZAI_API_KEY fehlt (provider: glm in config.yaml). .env anlegen "
            "(siehe .env.example) oder mit --dry-run ohne API testen."
        )
    glm_cfg = config.get("glm", {})
    base_url = glm_cfg.get("base_url", "https://openrouter.ai/api/v1").rstrip("/")
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": glm_cfg.get("model", "z-ai/glm-5.2"),
                "max_tokens": max_tokens,
                # GLM ist ein Reasoning-Modell und denkt per Default. OpenRouter
                # zählt die Reasoning-Tokens gegen max_tokens — bei langem Denken
                # ist das Budget aufgebraucht, bevor Inhalt kommt (finish_reason=
                # length, content leer). Fürs Lagebild reicht die direkte Antwort.
                "reasoning": {"enabled": False},
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=180,
        )
    except httpx.HTTPError as exc:
        raise _TransientError(str(exc)) from exc
    if resp.status_code in _RETRY_STATUS:
        raise _TransientError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    if resp.status_code != 200:
        raise RuntimeError(f"GLM-Fehler (HTTP {resp.status_code}): {resp.text[:300]}")
    data = resp.json()
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
    if not content or not content.strip():
        # Passiert v. a., wenn ein Upstream-Provider das reasoning-Flag ignoriert
        # und das Denken das Token-Budget frisst — nicht deterministisch, ein
        # neuer Versuch (ggf. anderer Provider) hat gute Chancen.
        raise _TransientError(f"GLM-Antwort ohne Inhalt: {str(data)[:300]}")
    return content.strip()
