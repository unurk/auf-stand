"""CLI: python -m auf_stand.main morgen|abend|catchup|feeds [--dry-run] [--keep-seen]"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from . import deliver, render, state, synthesize, telegram, tts, webpush
from .fetch import fetch_all, filter_recent

BASE_DIR = Path(__file__).resolve().parent.parent


def load_config() -> dict:
    return yaml.safe_load((BASE_DIR / "config.yaml").read_text(encoding="utf-8"))


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


def run_edition(edition: str, config: dict, dry_run: bool, keep_seen: bool) -> int:
    editions = config.get("editions", {})
    if edition not in editions:
        print(f"Unbekannte Ausgabe '{edition}'. Verfügbar: {', '.join(editions)}")
        return 1
    edition_config = editions[edition]

    result = fetch_all(config)
    for error in result.errors:
        print(f"Warnung: {error}")
    if not result.articles and edition != "catchup":
        print("Keine Artikel geladen — Abbruch. `feeds` zum Diagnostizieren ausführen.")
        return 1

    current_state = state.load_state()
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
    prompt = synthesize.build_prompt(
        selection,
        all_topics,
        edition_config.get("label", edition),
        termine=config.get("termine", []),
        dossier=current_state.get("dossier", {}),
        article_feedback_hint=fb_hint,
        user_topic_prefs=current_state.get("user_topic_prefs") or None,
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
    secs = max(60, round(words / 3.2 / 15) * 15)  # ~3.2 Wörter/Sek (Deutsch), auf 15s gerundet
    lagebild = re.sub(
        r"Lesezeit ca\.\s*\d+\s*Sekunden", f"Lesezeit ca. {secs} Sekunden", lagebild
    )
    # Redakteur:innen-Fußzeile aus den je Punkt genannten „Bericht: …"-Namen.
    lagebild = render.insert_reporters_footer(lagebild)
    from . import epaper as epaper_module
    lagebild += epaper_module.epaper_section(epaper_module.get_epaper_url(config))
    md_path, html_path = render.write_output(lagebild, edition)
    print(f"Lagebild erzeugt:\n  {md_path}\n  {html_path}")

    subject = f"{config.get('mail_subject_prefix', 'Auf Stand')} — {edition_config.get('label', edition)}"
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
                    "Dein Lagebild zum Hören",
                    config.get("telegram_chat_ids", []),
                    title=edition_config.get("label", edition),
                )
        except Exception as exc:
            print(f"Audio-Schritt übersprungen: {exc}")

    # Web-Push an PWA-Abonnenten (nur wenn VAPID konfiguriert ist).
    if webpush.webpush_configured():
        title_match = re.search(r"^#\s+(.+)$", lagebild, re.MULTILINE)
        push_title = title_match.group(1).strip() if title_match else "Dein Lagebild"
        push_body = article_headings[0] if article_headings else "Dein Lagebild ist da."
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
    result = fetch_all(config)
    articles = filter_recent(result.articles, 72)
    if not articles:
        print("Keine Artikel der letzten 72 Stunden gefunden.")
        return 1
    prompt = synthesize.build_prompt(
        articles, config.get("topics", []), "Catch-up · die letzten Tage in 4 Minuten"
    )
    if dry_run:
        path = render.OUT_DIR / f"{datetime.now():%Y-%m-%d}-catchup-prompt.txt"
        render.OUT_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(prompt, encoding="utf-8")
        print(f"Dry-Run: Prompt gespeichert unter {path}")
        return 0
    lagebild = synthesize.synthesize(prompt, config)
    md_path, html_path = render.write_output(lagebild, "catchup")
    print(f"Catch-up erzeugt:\n  {md_path}\n  {html_path}")
    return 0


def main() -> int:
    load_dotenv(BASE_DIR / ".env")
    parser = argparse.ArgumentParser(description="Auf Stand — Lagebild-Generator")
    parser.add_argument("command", choices=["morgen", "abend", "catchup", "feeds", "test-fulltext", "woche", "rueckkanal", "site", "vapid-keys"])
    parser.add_argument("--url", help="URL für test-fulltext")
    parser.add_argument("--dry-run", action="store_true", help="Prompt bauen, kein API-Call")
    parser.add_argument(
        "--keep-seen", action="store_true",
        help="State nicht aktualisieren (zum wiederholten Testen)",
    )
    args = parser.parse_args()

    config: dict = {}
    try:
        config = load_config()
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
            webview.build_site()
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
        return run_edition(args.command, config, args.dry_run, args.keep_seen)
    except Exception as exc:
        telegram.send_alert(
            f"❌ Auf Stand: Lauf '{args.command}' fehlgeschlagen: {exc}",
            config.get("telegram_chat_ids", []),
        )
        raise


if __name__ == "__main__":
    sys.exit(main())
