"""CLI: python -m copilot.main morgen|mittag|nachmittag|abend|catchup|feeds [--dry-run] [--keep-seen]"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from dotenv import load_dotenv

from . import deliver, i18n, render, state, synthesize, telegram, tts, webpush
from .fetch import fetch_all, filter_recent

BASE_DIR = Path(__file__).resolve().parent.parent


def load_config(path: str = "config.yaml") -> dict:
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = BASE_DIR / config_path
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def cmd_feeds(config: dict) -> int:
    """Verifiziert die konfigurierten Feeds."""
    result = fetch_all(config)
    by_ressort: dict[str, int] = {}
    for article in result.articles:
        by_ressort[article.ressort] = by_ressort.get(article.ressort, 0) + 1
    for feed in config.get("feeds", []):
        count = by_ressort.get(feed["name"], 0)
        status = f"OK, {count} Artikel" if count else "KEINE Artikel"
        print(f"  {feed['name']:<14} {status}   {feed['url']}")
    for error in result.errors:
        print(f"  FEHLER: {error}")
    if not result.articles:
        print(
            "\nKein Feed lieferbar. URLs auf diepresse.com prüfen "
            "(Schema kann sich geändert haben) und config.yaml anpassen."
        )
        return 1
    return 0


# Vorlauf: Wie viele Minuten VOR dem Slot bereits erzeugt werden darf. So ist das
# Lagebild rechtzeitig deployt; die Webapp enthüllt es dann punktgenau zum Slot.
AUTO_LEAD = timedelta(minutes=40)
VIENNA = ZoneInfo("Europe/Vienna")


def pick_auto_edition(config: dict, now: datetime | None = None) -> str | None:
    """Wählt anhand der Wiener Uhrzeit die aktuell fällige Ausgabe.

    Zeitzonensicher (Europe/Vienna, ganzjährig), unabhängig von der UTC-Uhr des
    CI-Runners — ersetzt den früheren `date -u +%H`-Fallback im Workflow.

    Zurückgegeben wird der jüngste Slot, dessen Vorlauf-Fenster (`Slot − AUTO_LEAD`)
    bereits begonnen hat — z. B. ab 05:20 → ``morgen``, ab 10:20 → ``mittag``.
    Vor dem ersten Slot des Tages (frühe Nacht) → ``None`` (nichts zu tun; die
    Abend-Ausgabe des Vortags deckt diese Zeit ab). Der Block-Guard verhindert
    weiterhin Doppelausgaben bei mehrfachen/verspäteten Läufen.
    """
    if now is None:
        now = datetime.now(VIENNA)
    chosen: str | None = None
    for edition, cfg in config.get("editions", {}).items():
        slot_str = cfg.get("time")
        if not slot_str:
            continue
        try:
            hh, mm = (int(x) for x in slot_str.split(":"))
        except (ValueError, AttributeError):
            continue
        slot = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if now >= slot - AUTO_LEAD:
            chosen = edition
    return chosen


def run_edition(edition: str, config: dict, dry_run: bool, keep_seen: bool) -> int:
    editions = config.get("editions", {})
    if edition not in editions:
        print(f"Unbekannte Ausgabe '{edition}'. Verfügbar: {', '.join(editions)}")
        return 1
    edition_config = editions[edition]
    lang = config.get("language", "de")
    prompt_file = config.get("prompt_file", "lagebild.md")

    current_state = state.load_state()

    # Monotonie-Schutz — bewusst VOR dem Fetch, damit übersprungene Läufe weder
    # RSS abrufen noch einen API-Call auslösen. Ausgaben laufen pro Tag in fester
    # Reihenfolge (morgen→mittag→nachmittag→abend). Ist heute bereits ein gleich-
    # oder höherrangiger Block ausgeliefert, darf ein späterer Lauf für einen
    # früheren/gleichen Block nicht erneut synthetisieren oder pushen.
    # Das macht zweierlei robust:
    #  - verspätet gefeuerte Crons (z. B. ein 5 h zu später 11-Uhr-Cron, der
    #    nach der 16-Uhr-Ausgabe noch eine stale Mittags-Ausgabe nachschöbe);
    #  - die engmaschigen Wiederhol-Cron-Läufe je Ausgabe-Fenster (alle 30 Min):
    #    nur der erste liefert aus, alle weiteren werden still übersprungen.
    order = list(editions.keys())
    rank = order.index(edition)
    today = f"{datetime.now():%Y-%m-%d}"
    delivered_today = [
        order.index(s["edition"])
        for s in current_state.get("stats", [])
        if s.get("date") == today and s.get("edition") in order
    ]
    if delivered_today and max(delivered_today) >= rank:
        print(
            f"Block '{edition}' ist heute bereits durch eine gleich- oder höherrangige "
            f"Ausgabe abgedeckt — kein doppeltes Lagebild. "
            f"(Schutz vor verspäteten/doppelten/Wiederhol-Cron-Läufen)"
        )
        return 0

    result = fetch_all(config)
    for error in result.errors:
        print(f"Warnung: {error}")
    if not result.articles and edition != "catchup":
        print("Keine Artikel geladen — Abbruch. `feeds` zum Diagnostizieren ausführen.")
        return 1

    articles = filter_recent(result.articles, float(edition_config.get("lookback_hours", 18)))
    new_articles, _ = state.split_new(articles, current_state)

    # Morgen-Ausgabe: grosszuegig (auch ueber Nacht Gesehenes kann rein, solange im
    # Zeitfenster). Abend-Ausgabe: strikt nur Neues seit der letzten Ausgabe.
    selection = articles if edition == "morgen" else new_articles
    if not selection:
        print("Nichts Neues seit der letzten Ausgabe — kein Lagebild nötig. (Feature!)")
        return 0
    print(f"{len(selection)} Artikel im Zeitfenster, davon {len(new_articles)} neu.")

    from datetime import timedelta
    all_topics = config.get("topics", []) + current_state.get("custom_topics", [])
    cutoff = (datetime.now() - timedelta(days=30)).date().isoformat()
    fb_hint = state.article_feedback_hint(current_state, cutoff)

    # Nächste Ausgabe im Presse-Takt bestimmen (Reihenfolge = config-Reihenfolge).
    nxt = order[(rank + 1) % len(order)]
    when_key = "when_tomorrow" if rank == len(order) - 1 else "when_today"
    next_edition = i18n.t(lang, "next_edition_fmt").format(
        when=i18n.t(lang, when_key), time=editions[nxt].get("time", "")
    )

    prompt = synthesize.build_prompt(
        selection,
        all_topics,
        edition_config.get("label", edition),
        termine=config.get("termine", []),
        dossier=current_state.get("dossier", {}),
        article_feedback_hint=fb_hint,
        user_topic_prefs=current_state.get("user_topic_prefs") or None,
        next_edition=next_edition,
        edition_emoji=edition_config.get("emoji", "☀️"),
        show_vorausschau=(edition == "morgen"),
        lang=lang,
        prompt_file=prompt_file,
    )

    if dry_run:
        out = render.OUT_DIR
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{datetime.now():%Y-%m-%d}-{edition}-prompt.txt"
        path.write_text(prompt, encoding="utf-8")
        print(f"Dry-Run: Prompt gespeichert unter {path} — kein API-Call.")
        return 0

    lagebild = synthesize.synthesize(prompt, config)
    # Lesezeit ehrlich machen: aus der tatsächlichen Wortzahl statt hartem "90".
    import re
    words = len(re.findall(r"\w+", lagebild))
    wps = float(i18n.t(lang, "words_per_sec"))
    secs = max(60, round(words / wps / 15) * 15)  # Wörter/Sek je Sprache, auf 15s gerundet
    lagebild = re.sub(
        i18n.t(lang, "reading_time_re"),
        i18n.t(lang, "reading_time_fmt").format(secs=secs),
        lagebild,
    )
    # Redakteur:innen-Fußzeile aus den je Punkt genannten Reporter-Namen.
    lagebild = render.insert_reporters_footer(lagebild, lang)
    from . import epaper as epaper_module
    lagebild += epaper_module.epaper_section(epaper_module.get_epaper_url(config), lang)
    md_path, html_path = render.write_output(lagebild, edition, lang)
    print(f"Lagebild erzeugt:\n  {md_path}\n  {html_path}")

    subject = f"{config.get('mail_subject_prefix', 'Copilot')} — {edition_config.get('label', edition)}"
    deliver.send_email(
        subject, lagebild, html_path.read_text(encoding="utf-8"), config.get("recipients", [])
    )
    feedback_key = (
        f"{datetime.now():%Y-%m-%d}|{edition}"
        if config.get("feedback_enabled", True)
        else None
    )
    import re
    article_headings = [
        re.sub(r"^[1-9]\S*\s+", "", line[3:]).strip()
        for line in lagebild.splitlines()
        if line.startswith("## ") and re.match(r"## [1-9]", line)
    ]
    telegram.send_telegram(
        lagebild,
        config.get("telegram_chat_ids", []),
        feedback_key=feedback_key,
        article_headings=article_headings or None,
    )

    # Audio-Ausgabe: das Lagebild zum Hören (best-effort, blockiert nie den Versand).
    if tts.tts_configured(config):
        try:
            mp3 = tts.generate_lagebild_audio(lagebild, edition, config)
            if mp3:
                telegram.send_audio(
                    mp3,
                    i18n.t(lang, "audio_caption"),
                    config.get("telegram_chat_ids", []),
                    title=edition_config.get("label", edition),
                )
        except Exception as exc:
            print(f"Audio-Schritt übersprungen: {exc}")

    # Web-Push an PWA-Abonnenten (nur wenn VAPID konfiguriert ist).
    if webpush.webpush_configured():
        title_match = re.search(r"^#\s+(.+)$", lagebild, re.MULTILINE)
        push_title = title_match.group(1).strip() if title_match else i18n.t(lang, "push_title_fallback")
        push_body = article_headings[0] if article_headings else i18n.t(lang, "push_body_fallback")
        site_url = config.get("site_url", "https://unurk.github.io/auf-stand/")
        webpush.send_push(push_title, push_body, site_url, current_state, config)

    if not keep_seen:
        points = len(re.findall(r"^## [0-9]", lagebild, re.MULTILINE))
        state.save_topic_articles(current_state, all_topics, result.articles)
        state.mark_seen(articles, current_state, edition)
        state.record_stats(
            current_state, edition, points, len(lagebild.split()), len(new_articles)
        )
        state.update_dossier(
            current_state, lagebild, all_topics, f"{datetime.now():%Y-%m-%d}"
        )
        questions = synthesize.generate_assessment_questions(result.articles, all_topics, config)
        if questions:
            current_state["assessment_questions"] = questions
        state.save_state(current_state)
    return 0


def cmd_catchup(config: dict, dry_run: bool) -> int:
    """Catch-up: alles aus den letzten 72 h, unabhängig vom Gesehen-Status."""
    lang = config.get("language", "de")
    prompt_file = config.get("prompt_file", "lagebild.md")
    result = fetch_all(config)
    articles = filter_recent(result.articles, 72)
    if not articles:
        print("Keine Artikel der letzten 72 Stunden gefunden.")
        return 1
    prompt = synthesize.build_prompt(
        articles,
        config.get("topics", []),
        i18n.t(lang, "catchup_label"),
        lang=lang,
        prompt_file=prompt_file,
    )
    if dry_run:
        path = render.OUT_DIR / f"{datetime.now():%Y-%m-%d}-catchup-prompt.txt"
        render.OUT_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(prompt, encoding="utf-8")
        print(f"Dry-Run: Prompt gespeichert unter {path}")
        return 0
    lagebild = synthesize.synthesize(prompt, config)
    md_path, html_path = render.write_output(lagebild, "catchup", lang)
    print(f"Catch-up erzeugt:\n  {md_path}\n  {html_path}")
    return 0


def main() -> int:
    load_dotenv(BASE_DIR / ".env")
    parser = argparse.ArgumentParser(description="Copilot — Lagebild-Generator")
    parser.add_argument("command", choices=["auto", "morgen", "mittag", "nachmittag", "abend", "catchup", "feeds", "test-fulltext", "woche", "rueckkanal", "site", "vapid-keys"])
    parser.add_argument("--url", help="URL für test-fulltext")
    parser.add_argument(
        "--config", default="config.yaml",
        help="Config-Datei (z. B. config.nyt.yaml für die englische NYT-Edition)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Prompt bauen, kein API-Call")
    parser.add_argument(
        "--keep-seen", action="store_true",
        help="State nicht aktualisieren (zum wiederholten Testen)",
    )
    args = parser.parse_args()

    config: dict = {}
    try:
        config = load_config(args.config)
        # Eigener State-Pfad je Edition (config.nyt.yaml -> data/state.nyt.json),
        # damit NYT- und Presse-Lauf getrennte „seen"-/Dossier-Stände führen.
        state.set_state_path(config.get("state_file"))
        # Ausgabeverzeichnis je Edition (config.nyt.yaml -> out/nyt/).
        render.set_out_dir(config.get("out_dir"))
        if args.command == "feeds":
            return cmd_feeds(config)
        if args.command == "catchup":
            return cmd_catchup(config, args.dry_run)
        if args.command == "woche":
            from . import quittung
            return quittung.cmd_woche(config)
        if args.command == "rueckkanal":
            from . import rueckkanal
            return rueckkanal.cmd_rueckkanal(config)
        if args.command == "site":
            from . import webview
            webview.build_site(config)
            return 0
        if args.command == "vapid-keys":
            pub, priv = webpush.generate_vapid_keys()
            print("VAPID-Schlüsselpaar erzeugt — als GitHub-Secrets / in .env hinterlegen:\n")
            print(f"VAPID_PUBLIC_KEY={pub}")
            print(f"VAPID_PRIVATE_KEY={priv}")
            print("VAPID_SUBJECT=mailto:unur@gmx.at")
            return 0
        if args.command == "test-fulltext":
            if not args.url:
                print("Fehler: --url <URL> angeben.")
                return 1
            from . import fulltext
            fulltext.test_url(args.url)
            return 0
        command = args.command
        if command == "auto":
            command = pick_auto_edition(config)
            if command is None:
                print(
                    "Kein aktiver Ausgabe-Slot zur jetzigen Wiener Uhrzeit "
                    "(vor dem Morgen-Fenster) — nichts zu tun."
                )
                return 0
            print(f"auto → Ausgabe '{command}' (nach Wiener Uhrzeit gewählt).")
        return run_edition(command, config, args.dry_run, args.keep_seen)
    except Exception as exc:
        telegram.send_alert(
            f"❌ Copilot: Lauf '{args.command}' fehlgeschlagen: {exc}",
            config.get("telegram_chat_ids", []),
        )
        raise


if __name__ == "__main__":
    sys.exit(main())
