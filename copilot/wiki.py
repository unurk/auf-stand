"""Themen-Wiki — Claude-gepflegte Wissensbasis je Thema (Karpathy „LLM Wiki").

Statt den Themen-Verlauf second-hand aus der fertigen Ausgabe zu parsen (so wie
state.update_dossier es tut), pflegt dieses Modul pro Thema eine first-hand aus den
QUELL-Artikeln gespeiste Markdown-Seite unter data/wiki/<slug>.md. Drei Operationen
nach Karpathy: ingest (Seite aus neuen Artikeln neu schreiben), query (nur den kurzen
„## Stand"-Kopf in den Synthese-Prompt geben), lint (wöchentliche Wartung).

Rein interner Mechanismus zur Schärfung des Deltas — keine browsebare Leser-Seite.
Einzige menschliche Fläche: die .md-Datei selbst (für die Redaktion) und der bereits
bestehende „Stand:"-Einzeiler im Webview (gespeist aus dem gleichen Ingest-Call).

Alles dry-run-sicher: ohne ANTHROPIC_API_KEY bzw. mit dry_run werden keine API-Calls
ausgelöst. Verzeichnis-Routing je Edition wie state.set_state_path / render.set_out_dir.
"""
from __future__ import annotations

import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
WIKI_DIR: Path = _BASE_DIR / "data" / "wiki"

# Caps spiegeln die Dossier-Logik (state.update_dossier): Verlauf schlank halten.
MAX_VERLAUF_LINES = 10
VERLAUF_MAX_DAYS = 30
MAX_ARTICLES_PER_TOPIC = 5  # wie state.save_topic_articles


def set_wiki_dir(path: str | None) -> None:
    """Setzt das Wiki-Verzeichnis (z. B. 'data/wiki.nyt' für die NYT-Edition).

    None lässt den Default (data/wiki). Relative Pfade werden auf das Projekt-
    Wurzelverzeichnis bezogen — gleiches Muster wie set_state_path / set_out_dir,
    damit parallele Editionen getrennte Wiki-Stände führen.
    """
    global WIKI_DIR
    if not path:
        return
    p = Path(path)
    WIKI_DIR = p if p.is_absolute() else _BASE_DIR / p


def _slug(name: str) -> str:
    """Stabiler ASCII-Dateiname aus einem Themennamen (lowercase, Bindestriche)."""
    norm = unicodedata.normalize("NFKD", name)
    ascii_str = norm.encode("ascii", "ignore").decode("ascii").lower()
    ascii_str = re.sub(r"[^a-z0-9]+", "-", ascii_str).strip("-")
    return ascii_str or "thema"


def _page_path(name: str) -> Path:
    return WIKI_DIR / f"{_slug(name)}.md"


def read_page(name: str) -> str:
    """Liest die Themenseite; "" wenn sie (noch) nicht existiert."""
    path = _page_path(name)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def write_page(name: str, markdown: str) -> None:
    """Schreibt die Themenseite (legt das Verzeichnis bei Bedarf an)."""
    path = _page_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown.rstrip() + "\n", encoding="utf-8")


def _section(markdown: str, heading: str) -> str:
    """Text eines '## <heading>'-Abschnitts bis zur nächsten '## '-Überschrift."""
    lines = markdown.splitlines()
    out: list[str] = []
    in_section = False
    for raw in lines:
        if raw.startswith("## "):
            if in_section:
                break
            in_section = raw[3:].strip().lower() == heading.lower()
            continue
        if in_section:
            out.append(raw)
    return "\n".join(out).strip()


def extract_stand(markdown: str) -> str:
    """Der '## Stand'-Kopf — der einzige Teil, der in den Synthese-Prompt geht."""
    return _section(markdown, "Stand")


def stand_oneliner(markdown: str) -> str:
    """Erste nicht-leere Stand-Zeile (für den Webview-„Stand:"), markdown-bereinigt."""
    stand = extract_stand(markdown)
    for line in stand.splitlines():
        clean = line.strip().lstrip("-• ").strip()
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
        clean = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", clean)
        if clean:
            return clean
    return ""


def current_stands(topics: list) -> dict[str, str]:
    """{Themenname: Stand-Kopf} für alle Themen mit vorhandener, nicht-leerer Seite.

    Reines Datei-Lesen — dry-run-sicher, kein API-Call.
    """
    from .synthesize import topic_name

    result: dict[str, str] = {}
    for topic in topics:
        name = topic_name(topic)
        stand = extract_stand(read_page(name))
        if stand:
            result[name] = stand
    return result


def _build_page(name: str, stand: str, offene_fragen: list[str], verlauf: list[str]) -> str:
    """Baut die Markdown-Seite aus ihren Abschnitten."""
    parts = [f"# {name}", "", "## Stand", stand.strip() or "—", "", "## Offene Fragen"]
    parts += [f"- {q}" for q in offene_fragen] or ["- —"]
    parts += ["", "## Verlauf"]
    parts += verlauf or ["- —"]
    return "\n".join(parts)


def migrate_dossier_to_wiki(dossier: dict, topics: list) -> None:
    """Seedet fehlende Themenseiten aus dem bestehenden flachen state["dossier"].

    Reines Text-Mapping, KEIN API-Call (dry-run-sicher). Existiert bereits eine Seite,
    wird sie nicht angefasst. So funktioniert das Feature ab dem ersten Einschalten,
    ohne dass der bisherige Themen-Verlauf verloren geht.
    """
    from .synthesize import topic_name

    for topic in topics:
        name = topic_name(topic)
        if read_page(name):
            continue
        entries = dossier.get(name, [])
        if not entries:
            continue
        # Neueste zuerst; Stand = jüngster Eintrag.
        ordered = sorted(entries, key=lambda e: e.get("date", ""), reverse=True)
        stand = ordered[0].get("summary", "").strip()
        verlauf = []
        for e in ordered:
            d = e.get("date", "")
            tag = f"[{d[8:10]}.{d[5:7]}.] " if len(d) >= 10 else ""
            verlauf.append(f"- {tag}{e.get('summary', '').strip()}")
        write_page(name, _build_page(name, stand, [], verlauf))


def _matched_articles(name: str, keyword: str, articles: list) -> list:
    """Artikel zum Thema per Schlagwort (gleiche Semantik wie save_topic_articles)."""
    kw = (keyword or "").lower()
    if not kw:
        return []
    matched = [
        a for a in articles
        if kw in a.title.lower() or kw in (getattr(a, "teaser", "") or "").lower()
    ]
    matched.sort(
        key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    return matched[:MAX_ARTICLES_PER_TOPIC]


def ingest(
    state: dict,
    topics: list,
    new_articles: list,
    datum: str,
    config: dict,
    dry_run: bool = False,
) -> dict[str, str]:
    """Aktualisiert je Thema mit ≥1 neuem passenden Artikel die Wiki-Seite via Claude.

    Liest die aktuelle Seite, lässt Claude (Haiku) sie neu schreiben (Stand
    aktualisieren, Widersprüche auflösen, Verlauf datiert ergänzen, Offene Fragen
    pflegen), schreibt sie zurück und liefert je Thema den Stand-Einzeiler zurück —
    damit der Aufrufer ihn in state["dossier"] für den Webview falten kann.

    Guard: dry_run oder fehlender ANTHROPIC_API_KEY ⇒ {} (kein Call). Fehler je
    Thema werden geschluckt (best-effort), der Lauf läuft weiter.
    """
    from .synthesize import topic_keyword, topic_name

    if dry_run or not os.environ.get("ANTHROPIC_API_KEY"):
        return {}

    stands: dict[str, str] = {}
    for topic in topics:
        name = topic_name(topic)
        matched = _matched_articles(name, topic_keyword(topic), new_articles)
        if not matched:
            continue
        try:
            new_md = _ingest_one(name, read_page(name), matched, datum, config)
        except Exception as exc:  # best-effort, nie blockierend
            print(f"wiki.ingest Fehler bei '{name}': {exc}")
            continue
        if not new_md:
            continue
        write_page(name, new_md)
        oneliner = stand_oneliner(new_md)
        if oneliner:
            stands[name] = oneliner
    return stands


def _ingest_one(name: str, current_md: str, articles: list, datum: str, config: dict) -> str | None:
    """Ein Claude-Call (Haiku): schreibt die Themenseite neu. Muster wie assess_quality()."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None

    article_block = "\n".join(
        f"- [{a.ressort}] {a.title}: {(getattr(a, 'teaser', '') or '')[:240]}"
        for a in articles
    )
    lang = config.get("language") or "de"
    current = current_md.strip() or "(noch keine Seite — neu anlegen)"
    if lang == "en":
        prompt = (
            "You maintain a per-topic knowledge base page in markdown for a news desk.\n"
            f"Topic: {name}\nToday: {datum}\n\n"
            f"Current page:\n---\n{current}\n---\n\n"
            f"New source articles for this topic:\n{article_block}\n\n"
            "Rewrite the FULL page in this exact structure:\n"
            "# <topic>\n## Stand\n<3-6 lines: the consolidated current state, "
            "resolving any contradictions with the new articles>\n"
            "## Offene Fragen\n- <open questions, if any>\n"
            "## Verlauf\n- [DD.MM.] <dated development, newest first, "
            f"keep at most {MAX_VERLAUF_LINES} lines>\n\n"
            "Be factual and concise; only use what the page and the articles support. "
            "Reply with ONLY the markdown page, no commentary."
        )
    else:
        prompt = (
            "Du pflegst für eine Nachrichtenredaktion eine Themen-Wissensbasis als Markdown-Seite.\n"
            f"Thema: {name}\nHeute: {datum}\n\n"
            f"Aktuelle Seite:\n---\n{current}\n---\n\n"
            f"Neue Quell-Artikel zum Thema:\n{article_block}\n\n"
            "Schreibe die GESAMTE Seite neu, exakt in dieser Struktur:\n"
            "# <Thema>\n## Stand\n<3–6 Zeilen: der konsolidierte aktuelle Stand, "
            "Widersprüche mit den neuen Artikeln auflösen>\n"
            "## Offene Fragen\n- <offene Fragen, falls vorhanden>\n"
            "## Verlauf\n- [DD.MM.] <datierte Entwicklung, neueste zuerst, "
            f"höchstens {MAX_VERLAUF_LINES} Zeilen>\n\n"
            "Sachlich und knapp; nur was Seite und Artikel hergeben. "
            "Antworte NUR mit der Markdown-Seite, ohne Kommentar."
        )

    client = anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=config.get("judge_model", "claude-haiku-4-5-20251001"),
        max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    # Robust: vom ersten '# ' an nehmen, falls das Modell etwas voranstellt.
    m = re.search(r"^#\s.*", text, re.DOTALL | re.MULTILINE)
    page = m.group() if m else text
    return page.strip() or None


def _verlauf_dates(markdown: str) -> list[str]:
    """ISO-untaugliche [DD.MM.]-Tags aus dem Verlauf — für die Staleness-Heuristik."""
    return re.findall(r"\[(\d{2})\.(\d{2})\.\]", _section(markdown, "Verlauf"))


def lint_wiki(topics: list, config: dict, stale_days: int = 14) -> str:
    """Wöchentlicher Wartungs-Pass: markiert veraltete Themen + (optional) Widersprüche.

    Heuristik ohne API: Themen ohne Verlauf-Eintrag seit > stale_days gelten als
    veraltet/abgeschlossen. Schreibt data/wiki/_lint.log (redaktionsintern) und gibt
    eine kurze Summary zurück. Nicht blockierend — Fehler werden geschluckt.
    """
    from .synthesize import topic_name

    now = datetime.now(timezone.utc)
    stale: list[str] = []
    missing: list[str] = []
    ok = 0
    for topic in topics:
        name = topic_name(topic)
        md = read_page(name)
        if not md:
            missing.append(name)
            continue
        dates = _verlauf_dates(md)
        if not dates:
            stale.append(name)
            continue
        # Jüngsten Verlauf-Tag (Tag.Monat) auf das laufende/letzte Jahr beziehen.
        newest = None
        for dd, mm in dates:
            try:
                cand = datetime(now.year, int(mm), int(dd), tzinfo=timezone.utc)
                if cand > now:
                    cand = cand.replace(year=now.year - 1)
            except ValueError:
                continue
            newest = cand if newest is None or cand > newest else newest
        if newest is None or (now - newest).days > stale_days:
            stale.append(name)
        else:
            ok += 1

    lines = [
        f"# Wiki-Lint {now.date().isoformat()}",
        f"aktuell: {ok} · veraltet (>{stale_days}d): {len(stale)} · ohne Seite: {len(missing)}",
    ]
    if stale:
        lines.append("VERALTET/abgeschlossen prüfen: " + ", ".join(stale))
    if missing:
        lines.append("ohne Seite (noch kein Ingest): " + ", ".join(missing))
    log = "\n".join(lines)
    try:
        WIKI_DIR.mkdir(parents=True, exist_ok=True)
        (WIKI_DIR / "_lint.log").write_text(log + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"wiki.lint_wiki: Log konnte nicht geschrieben werden: {exc}")
    return lines[1]
