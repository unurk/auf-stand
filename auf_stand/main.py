"""CLI: python -m auf_stand.main morgen|abend|catchup|feeds [--dry-run] [--keep-seen]"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

from . import deliver, render, state, synthesize, telegram
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

    prompt = synthesize.build_prompt(
        selection,
        config.get("topics", []),
        edition_config.get("label", edition),
        termine=config.get("termine", []),
    )

    if dry_run:
        out = render.OUT_DIR
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{datetime.now():%Y-%m-%d}-{edition}-prompt.txt"
        path.write_text(prompt, encoding="utf-8")
        print(f"Dry-Run: Prompt gespeichert unter {path} — kein API-Call.")
        return 0

    lagebild = synthesize.synthesize(prompt, config)
    md_path, html_path = render.write_output(lagebild, edition)
    print(f"Lagebild erzeugt:\n  {md_path}\n  {html_path}")

    subject = f"{config.get('mail_subject_prefix', 'Auf Stand')} — {edition_config.get('label', edition)}"
    deliver.send_email(
        subject, lagebild, html_path.read_text(encoding="utf-8"), config.get("recipients", [])
    )
    telegram.send_telegram(lagebild, config.get("telegram_chat_ids", []))

    if not keep_seen:
        import re
        points = len(re.findall(r"^## [0-9]", lagebild, re.MULTILINE))
        state.mark_seen(articles, current_state, edition)
        state.record_stats(
            current_state, edition, points, len(lagebild.split()), len(new_articles)
        )
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
    parser.add_argument("command", choices=["morgen", "abend", "catchup", "feeds", "test-fulltext", "woche", "rueckkanal"])
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
