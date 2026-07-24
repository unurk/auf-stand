"""Zentrale Sprach-Tabelle für die Ausgabe-Lokalisierung.

Das deutsche Presse-Produkt ist der Default ("de") — die Werte hier entsprechen
exakt den bisher hart verdrahteten Strings, damit sich an der Presse-Ausgabe
nichts ändert. "en" liefert die NYT-Variante (englisches „Today's Paper"-Briefing).

Pro Edition wird die Sprache über config.yaml (`language: de|en`) gewählt und durch
die Pipeline gereicht. Module rufen `t(lang, key)` bzw. die Wochentag-/Monatslisten.
"""
from __future__ import annotations

STRINGS: dict[str, dict] = {
    "de": {
        # Kalender (synthesize.date_label — lang; vorausschau — kurz)
        "weekdays": [
            "Montag", "Dienstag", "Mittwoch", "Donnerstag",
            "Freitag", "Samstag", "Sonntag",
        ],
        "months": [
            "Jänner", "Februar", "März", "April", "Mai", "Juni",
            "Juli", "August", "September", "Oktober", "November", "Dezember",
        ],
        "weekdays_short": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
        "months_short": [
            "Jän", "Feb", "Mär", "Apr", "Mai", "Jun",
            "Jul", "Aug", "Sep", "Okt", "Nov", "Dez",
        ],
        # {weekday} {day} {month} {year} {edition}
        "date_label_fmt": "{weekday}, {day}. {month} {year} · {edition}",
        # Nächste-Ausgabe-Hinweis (Footer)
        "next_edition_fmt": "Nächstes Lagebild: {when} {time} Uhr.",
        "when_today": "heute",
        "when_tomorrow": "morgen",
        # Lesezeit-Postprocessing (main.py)
        "reading_time_re": r"Lesezeit ca\.\s*\d+\s*Sekunden",
        "reading_time_fmt": "Lesezeit ca. {secs} Sekunden",
        "words_per_sec": 3.2,
        # Prompt-Material-Labels (synthesize.build_prompt)
        "tracker_hint": (
            "## Deine Themen\n[Nur falls es zu verfolgten Themen materielle "
            "Änderungen gibt — sonst Abschnitt weglassen]"
        ),
        # Vollständigkeits-Beweis (synthesize.build_prompt / webview-Rendering)
        "nicht_aufgenommen_hint": (
            "## 🔍 Geprüft, nicht aufgenommen\n[Nur wenn es ernsthafte Kandidaten "
            "gibt — max. 4 Zeilen, sonst Abschnitt weglassen]"
        ),
        "nicht_aufgenommen_marker": "Geprüft, nicht aufgenommen",
        "tracker_heading": "Deine Themen",
        "geprueft_fmt": "🔍 *{n} Meldungen geprüft* · {p} aufgenommen.",
        # Ruhe-Ausgabe (main.run_edition, wenn nichts die Schwelle erreicht)
        "ruhe_headline": "Ruhige Lage",
        "ruhe_body_fmt": (
            "**Ruhige Lage.** Seit der letzten Ausgabe hat keine der {n} geprüften "
            "Meldungen die Schwelle erreicht. Kein Handlungsbedarf."
        ),
        "ruhe_body_leer": (
            "**Ruhige Lage.** Seit der letzten Ausgabe ist nichts Wesentliches "
            "dazugekommen. Kein Handlungsbedarf."
        ),
        "ruhe_informed_fmt": "✅ *Du bist informiert — nichts zu tun. {next}*",
        "section_topics": "## Verfolgte Themen\n",
        "section_fulltexts": "## Volltexte (haben Vorrang)\n",
        "section_articles_fmt": "## Artikel aus den RSS-Feeds ({n} Stück)\n",
        "verlauf_prefix": "  Verlauf: ",
        "author_prefix": " — Autor: ",
        # Reporter-Fußzeile (render.insert_reporters_footer)
        "reporters_marker": r"Bericht:\s*([^)·\n]+)",
        "reporters_footer_fmt": "*Heute mit Berichterstattung von: {names} · Die Presse*",
        "reporters_join": "und",
        # „Du bist informiert"-Anker (render._markdown_to_html, footer-Einfügung)
        "informed_marker": "Du bist informiert",
        # Streak-Suffix in der Abschlusszeile (render.insert_streak)
        "streak_suffix_fmt": " — {n}. Tag in Folge",
        # Abend-Cliffhanger (vorausschau.format_morgen_teaser)
        "morgen_teaser_fmt": "🔭 *Morgen wichtig:* {items}",
        # HTML-Rendering (render)
        "brand": "Die Presse · Copilot",
        "byline": "Von der „Presse“-Redaktion",
        "html_lang": "de",
        "default_title": "Dein Lagebild",
        # E-Paper (epaper.epaper_section)
        "epaper_label": "Die Presse — E-Paper",
        "epaper_link_text": "Aktuelle Ausgabe öffnen →",
        # Vorausschau (vorausschau.format_vorausschau)
        "vorausschau_heading": "## 📅 Diese Woche noch",
        "vorausschau_date_fmt": "{weekday} {day}. {month}.",
        "vorausschau_tracker_fmt": " — betrifft Tracker „{tracker}“",
        # Telegram / Push
        "audio_caption": "Dein Lagebild zum Hören",
        "push_title_fallback": "Dein Lagebild",
        "push_body_fallback": "Dein Lagebild ist da.",
        "catchup_label": "Catch-up · die letzten Tage in 4 Minuten",
        # Teilbare Punkt-Karte (karte.py) und Podcast-Feed (podcast.py)
        "karte_footer": "Dein Lagebild · 4× täglich · diepresse.com",
        "podcast_title": "Die Presse · Copilot — Dein Lagebild",
        "podcast_subtitle": "Vier Ausgaben täglich. In 90 Sekunden auf Stand.",
        "podcast_description": (
            "Das Lagebild der „Presse“ zum Hören: viermal täglich (6, 11, 16 und 20 Uhr) "
            "die Entwicklungen, die sich materiell geändert haben — in rund 90 Sekunden."
        ),
        "podcast_author": "Die Presse",
    },
    "en": {
        "weekdays": [
            "Monday", "Tuesday", "Wednesday", "Thursday",
            "Friday", "Saturday", "Sunday",
        ],
        "months": [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ],
        "weekdays_short": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "months_short": [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ],
        "date_label_fmt": "{weekday}, {month} {day}, {year} · {edition}",
        "next_edition_fmt": "Next briefing: {when} at {time}.",
        "when_today": "today",
        "when_tomorrow": "tomorrow",
        "reading_time_re": r"reading time ca\.\s*\d+\s*seconds",
        "reading_time_fmt": "reading time ca. {secs} seconds",
        "words_per_sec": 3.3,
        "tracker_hint": (
            "## Your Topics\n[Only if there are material changes to tracked "
            "topics — otherwise omit this section]"
        ),
        "nicht_aufgenommen_hint": (
            "## 🔍 Checked, not included\n[Only if there are real candidates — "
            "max. 4 lines, otherwise omit the section]"
        ),
        "nicht_aufgenommen_marker": "Checked, not included",
        "tracker_heading": "Your Topics",
        "geprueft_fmt": "🔍 *{n} stories checked* · {p} included.",
        "ruhe_headline": "A quiet stretch",
        "ruhe_body_fmt": (
            "**A quiet stretch.** None of the {n} stories checked since the last "
            "briefing cleared the bar. Nothing to act on."
        ),
        "ruhe_body_leer": (
            "**A quiet stretch.** Nothing material has come in since the last "
            "briefing. Nothing to act on."
        ),
        "ruhe_informed_fmt": "✅ *You're informed — nothing to do. {next}*",
        "section_topics": "## Tracked Topics\n",
        "section_fulltexts": "## Full texts (take priority)\n",
        "section_articles_fmt": "## Articles from the RSS feeds ({n})\n",
        "verlauf_prefix": "  History: ",
        "author_prefix": " — Author: ",
        "reporters_marker": r"By:\s*([^)·\n]+)",
        "reporters_footer_fmt": "*Today's reporting by: {names} · The New York Times*",
        "reporters_join": "and",
        "informed_marker": "You're informed",
        "streak_suffix_fmt": " — day {n} in a row",
        "morgen_teaser_fmt": "🔭 *Tomorrow:* {items}",
        "brand": "The New York Times · Copilot",
        "byline": "By the New York Times briefing desk",
        "html_lang": "en",
        "default_title": "Your Briefing",
        "epaper_label": "The New York Times — Today's Paper",
        "epaper_link_text": "Open today's paper →",
        "vorausschau_heading": "## 📅 Still ahead this week",
        "vorausschau_date_fmt": "{weekday} {month} {day}",
        "vorausschau_tracker_fmt": " — affects tracker “{tracker}”",
        "audio_caption": "Your briefing — listen",
        "push_title_fallback": "Your Briefing",
        "push_body_fallback": "Your briefing is ready.",
        "catchup_label": "Catch-up · the last few days in 4 minutes",
        "karte_footer": "Your Briefing · 4× daily · nytimes.com",
        "podcast_title": "NYT Briefing · Copilot",
        "podcast_subtitle": "Four editions a day. Informed in 90 seconds.",
        "podcast_description": (
            "Your briefing to listen to: four times a day (6, 11, 16 and 20:00) the "
            "developments that materially changed — in about 90 seconds."
        ),
        "podcast_author": "The New York Times",
    },
}


def t(lang: str | None, key: str):
    """Lokalisierten Wert holen; fällt sprach- und schlüsselweise auf Deutsch zurück."""
    table = STRINGS.get(lang or "de", STRINGS["de"])
    if key in table:
        return table[key]
    return STRINGS["de"][key]
