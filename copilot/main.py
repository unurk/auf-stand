"""CLI: python -m copilot.main morgen|mittag|nachmittag|abend|catchup|feeds [--dry-run] [--keep-seen]"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml
from dotenv import load_dotenv

from . import (
    deliver, epaper, i18n, karte, profil, qualitaet, render, state, synthesize,
    telegram, tts, vorausschau, webpush,
)
from .fetch import fetch_all, filter_recent

BASE_DIR = Path(__file__).resolve().parent.parent

# Zeitbudget der Ausgabe in Sekunden — das Produktversprechen („rund 90 Sekunden").
# Wird nicht erzwungen (das würde Inhalt zerstören), aber gemessen und als
# Kalibrierung in den nächsten Prompt gegeben.
LESEZEIT_BUDGET = 90


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
    kaputt = 0
    for feed in config.get("feeds", []):
        count = by_ressort.get(feed["name"], 0)
        status = f"OK, {count} Artikel" if count else "KEINE Artikel"
        kaputt += 0 if count else 1
        print(f"  {feed['name']:<14} {status}   {feed['url']}")
    for error in result.errors:
        print(f"  FEHLER: {error}")
    if not result.articles:
        print(
            "\nKein Feed lieferbar. URLs auf diepresse.com prüfen "
            "(Schema kann sich geändert haben) und config.yaml anpassen."
        )
        return 1
    if kaputt:
        # Auch ein einzelner toter Feed ist ein Befund: Fehlt ein Ressort, fehlt
        # es still — die Ausgabe wird einfach ein bisschen ärmer. Exit-Code 1,
        # damit das beim manuellen Lauf und in CI auffällt.
        print(f"\n{kaputt} Feed(s) ohne Artikel — config.yaml prüfen.")
        return 1
    return 0


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

    # Nächste Ausgabe im Presse-Takt bestimmen (Reihenfolge = config-Reihenfolge).
    nxt = order[(rank + 1) % len(order)]
    when_key = "when_tomorrow" if rank == len(order) - 1 else "when_today"
    next_edition = i18n.t(lang, "next_edition_fmt").format(
        when=i18n.t(lang, when_key), time=editions[nxt].get("time", "")
    )

    # Morgen-Ausgabe: grosszuegig (auch ueber Nacht Gesehenes kann rein, solange im
    # Zeitfenster). Abend-Ausgabe: strikt nur Neues seit der letzten Ausgabe.
    selection = articles if edition == "morgen" else new_articles
    if not selection:
        # Stille wird zugestellt, nicht verschwiegen: Sonst ist „ruhiger Nachrichtentag"
        # von „Dienst kaputt" nicht unterscheidbar — und Vertrauen in die
        # Vollständigkeit ist die einzige Währung eines Hintergrund-Dienstes.
        return _ruhe_ausgabe(
            edition, edition_config, config, current_state, len(articles),
            next_edition, dry_run=dry_run, keep_seen=keep_seen, lang=lang,
        )
    print(f"{len(selection)} Artikel im Zeitfenster, davon {len(new_articles)} neu.")

    all_topics = config.get("topics", []) + current_state.get("custom_topics", [])
    cutoff = (datetime.now() - timedelta(days=30)).date().isoformat()
    fb_hint = state.article_feedback_hint(current_state, cutoff)
    missing_hint = state.missing_feedback_hint(current_state, cutoff)
    budget = int(config.get("lesezeit_budget_sekunden", LESEZEIT_BUDGET))
    budget_hint = qualitaet.budget_hinweis(state.letzte_lesezeiten(current_state), budget)

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
        profil=profil.get_profil(current_state),
        missing_hint=missing_hint,
        budget_hint=budget_hint,
    )

    if dry_run:
        out = render.OUT_DIR
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{datetime.now():%Y-%m-%d}-{edition}-prompt.txt"
        path.write_text(prompt, encoding="utf-8")
        print(f"Dry-Run: Prompt gespeichert unter {path} — kein API-Call.")
        return 0

    lagebild = synthesize.synthesize(prompt, config)
    # Qualitäts-Gate VOR der Lesezeit-Rechnung: leere Themen-Deltas („hat sich
    # nichts geändert") raus, Abschnitt auf 3 Zeilen kappen. Der Prompt verbietet
    # das zwar, hielt es im Archiv aber nachweislich nicht ein.
    lagebild, tracker_report = qualitaet.trim_tracker_section(
        lagebild, heading=i18n.t(lang, "tracker_heading")
    )
    if tracker_report["entfernt"] or tracker_report["gekappt"]:
        print(
            f"Qualitäts-Gate: {tracker_report['entfernt']} Themen-Zeile(n) entfernt, "
            f"{tracker_report['gekappt']} gekürzt, {tracker_report['behalten']} behalten."
        )
    # Lesezeit ehrlich machen: aus der tatsächlichen Wortzahl statt hartem "90".
    words = len(re.findall(r"\w+", lagebild))
    wps = float(i18n.t(lang, "words_per_sec"))
    secs = max(60, round(words / wps / 15) * 15)  # Wörter/Sek je Sprache, auf 15s gerundet
    warnung = qualitaet.pruefe_budget(lagebild, budget, wps)
    if warnung:
        print(warnung)
    lagebild = re.sub(
        i18n.t(lang, "reading_time_re"),
        i18n.t(lang, "reading_time_fmt").format(secs=secs),
        lagebild,
    )
    # Redakteur:innen-Fußzeile aus den je Punkt genannten Reporter-Namen.
    lagebild = render.insert_reporters_footer(lagebild, lang)
    # Abend-Cliffhanger: was morgen ansteht — ein Grund, die Morgen-Ausgabe zu öffnen.
    if edition == "abend":
        teaser = vorausschau.format_morgen_teaser(config.get("termine", []), lang)
        if teaser:
            lagebild = render.insert_before_footer(lagebild, teaser, lang)
    # Vollständigkeits-Beweis: wie viel geprüft wurde, wie wenig durchkam. Die
    # Zahl kommt aus der Pipeline (nicht vom Modell), die knapp verfehlten Titel
    # liefert der Prompt-Abschnitt „Geprüft, nicht aufgenommen".
    punkte_im_text = len(re.findall(r"^## [0-9]", lagebild, re.MULTILINE))
    lagebild = render.insert_before_footer(
        lagebild,
        i18n.t(lang, "geprueft_fmt").format(n=len(selection), p=punkte_im_text),
        lang,
    )
    # Streak in die Abschlusszeile. Sobald es Lese-Signale gibt, zählt Gelesenes
    # statt Zugestelltes — ein Streak, den unser eigener Cron erzeugt, misst uns,
    # nicht die Leserin.
    heute = f"{datetime.now():%Y-%m-%d}"
    streak, misst_lesen = state.streak(current_state)
    if not misst_lesen and not any(
        s.get("date") == heute for s in current_state.get("stats", [])
    ):
        streak += 1  # current_streak zählt heute erst nach record_stats (läuft später)
    lagebild = render.insert_streak(lagebild, streak, lang)
    lagebild += epaper.epaper_section(epaper.get_epaper_url(config), lang)
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
    article_headings = [
        re.sub(r"^[1-9]\S*\s+", "", line[3:]).strip()
        for line in lagebild.splitlines()
        if line.startswith("## ") and re.match(r"## [1-9]", line)
    ]
    # Punkt-Titel festhalten, damit 👍/👎-Taps später inhaltlich auflösbar sind
    # (der Rückkanal-Lauf lädt den State neu, darum hier sofort persistieren).
    state.save_edition_points(
        current_state, f"{datetime.now():%Y-%m-%d}", edition, article_headings
    )
    state.save_state(current_state)
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

    # Teilbare Karte zum wichtigsten Punkt (best-effort). Sie wird bewusst NICHT
    # gepusht — sie liegt in der App bereit, wenn jemand teilen will.
    karte.karte_fuer_ausgabe(
        lagebild,
        edition,
        edition_config.get("label", edition),
        out_dir=render.OUT_DIR,
        lang=lang,
    )

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
            current_state, edition, points, len(lagebild.split()), len(new_articles),
            secs=secs, geprueft=len(selection),
        )
        state.update_dossier(
            current_state, lagebild, all_topics, f"{datetime.now():%Y-%m-%d}"
        )
        questions = synthesize.generate_assessment_questions(result.articles, all_topics, config)
        if questions:
            current_state["assessment_questions"] = questions
        state.save_state(current_state)
    return 0


def _ruhe_ausgabe(
    edition: str,
    edition_config: dict,
    config: dict,
    current_state: dict,
    geprueft: int,
    next_edition: str,
    dry_run: bool,
    keep_seen: bool,
    lang: str,
) -> int:
    """Zustellung an ruhigen Blöcken: „Nichts Wesentliches. Du bist auf Stand."

    Früher endete der Lauf hier lautlos. Für die Leserin war damit nicht
    unterscheidbar, ob die Nachrichtenlage ruhig oder der Dienst kaputt war —
    und genau diese Unsicherheit zerstört das Vertrauen, von dem ein
    Hintergrund-Dienst als einzigem lebt. Kostet 3 Sekunden Lesezeit,
    braucht keinen API-Call.
    """
    heute = datetime.now()
    label = edition_config.get("label", edition)
    body = (
        i18n.t(lang, "ruhe_body_fmt").format(n=geprueft)
        if geprueft
        else i18n.t(lang, "ruhe_body_leer")
    )
    md = (
        f"# {edition_config.get('emoji', '☀️')} "
        f"{i18n.t(lang, 'default_title')} — "
        f"{synthesize.date_label(label, lang)}\n\n"
        f"## {i18n.t(lang, 'ruhe_headline')}\n"
        f"{body}\n\n"
        "---\n"
        + i18n.t(lang, "ruhe_informed_fmt").format(next=next_edition)
    )
    print(f"Ruhiger Block: nichts Neues, {geprueft} Meldungen geprüft.")
    if dry_run:
        print("Dry-Run: Ruhe-Ausgabe nicht zugestellt.")
        return 0

    streak, misst_lesen = state.streak(current_state)
    if not misst_lesen and not any(
        s.get("date") == f"{heute:%Y-%m-%d}" for s in current_state.get("stats", [])
    ):
        streak += 1
    md = render.insert_streak(md, streak, lang)
    md_path, html_path = render.write_output(md, edition, lang)
    print(f"Ruhe-Ausgabe erzeugt:\n  {md_path}\n  {html_path}")

    telegram.send_telegram(md, config.get("telegram_chat_ids", []))
    if not keep_seen:
        state.record_stats(
            current_state, edition, 0, len(md.split()), 0,
            secs=qualitaet.lesezeit_sekunden(md, float(i18n.t(lang, "words_per_sec"))),
            geprueft=geprueft,
        )
        state.save_state(current_state)
    return 0


def cmd_karte(config: dict) -> int:
    """Erzeugt die Teilen-Karte zur jüngsten Ausgabe neu (out/…-karte.png)."""
    lang = config.get("language", "de")
    editions = config.get("editions", {})
    dateien = sorted(render.OUT_DIR.glob("*-*.md"), reverse=True)
    for pfad in dateien:
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-([a-z]+)\.md$", pfad.name)
        if not m or m.group(2) not in editions:
            continue
        datum = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        edition = m.group(2)
        ziel = karte.karte_fuer_ausgabe(
            pfad.read_text(encoding="utf-8"),
            edition,
            editions[edition].get("label", edition),
            datum=datum,
            out_dir=render.OUT_DIR,
            lang=lang,
        )
        if ziel:
            print(f"Karte erzeugt: {ziel}")
            return 0
        print("Kein Punkt zum Rendern gefunden.")
        return 1
    print("Keine Ausgabe in out/ gefunden.")
    return 1


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
    parser.add_argument("command", nargs="?", default="auto",
                        choices=["auto", "morgen", "mittag", "nachmittag", "abend", "catchup", "feeds", "woche", "rueckkanal", "site", "karte", "vapid-keys"])
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
        if args.command == "auto":
            hour = datetime.now().hour
            if hour <= 8:
                args.command = "morgen"
            elif hour <= 13:
                args.command = "mittag"
            elif hour <= 17:
                args.command = "nachmittag"
            else:
                args.command = "abend"
            print(f"Auto-Modus: {args.command} (Uhrzeit {hour:02d}:xx)")
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
        if args.command == "karte":
            return cmd_karte(config)
        if args.command == "vapid-keys":
            pub, priv = webpush.generate_vapid_keys()
            print("VAPID-Schlüsselpaar erzeugt — als GitHub-Secrets / in .env hinterlegen:\n")
            print(f"VAPID_PUBLIC_KEY={pub}")
            print(f"VAPID_PRIVATE_KEY={priv}")
            print("VAPID_SUBJECT=mailto:unur@gmx.at")
            return 0
        return run_edition(args.command, config, args.dry_run, args.keep_seen)
    except Exception as exc:
        telegram.send_alert(
            f"❌ Copilot: Lauf '{args.command}' fehlgeschlagen: {exc}",
            config.get("telegram_chat_ids", []),
        )
        raise


if __name__ == "__main__":
    sys.exit(main())
