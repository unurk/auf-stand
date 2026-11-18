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
            "gibt — max. 4 Zeilen, Begründung nach Relevanz für den Leser (nicht "
            "„keine Gesetzesänderung“), sonst Abschnitt weglassen]"
        ),
        # Zweck je Ausgabe (synthesize.build_prompt → {AUSGABE_ZWECK})
        "zweck_heading": "## Zweck dieser Ausgabe",
        "zweck": {
            "morgen": (
                "**06:00 — Überblick.** Der Leser startet in den Tag und hat seit dem "
                "Vorabend nichts gelesen. Gib den Überblick: Was hat sich über Nacht und "
                "seit gestern Abend materiell geändert, was bestimmt den heutigen Tag? "
                "Hier dürfen auch Entwicklungen von gestern Abend stehen, sofern sie "
                "noch nicht im Lagebild waren. Das ist die einzige Ausgabe, in der bis "
                "zu 5 Punkte normal sind."
            ),
            "mittag": (
                "**11:00 — nur Neues seit dem Morgen.** Der Leser kennt die "
                "06-Uhr-Ausgabe. Bring ausschließlich, was seit dem Morgen neu ist oder "
                "sich gegenüber dem Morgenstand materiell bewegt hat. Wiederhole nichts "
                "aus „Heute bereits berichtet“ — außer mit echtem neuen Stand, dann "
                "beginne den Punkt mit „Update:“. 1–2 Punkte sind hier der Normalfall; "
                "ist nichts Wesentliches dazugekommen, ist das eine Ruhige Lage."
            ),
            "nachmittag": (
                "**16:00 — Update.** Was hat sich seit Mittag bewegt: neue "
                "Entscheidungen, Zahlen, Reaktionen mit Folgen? Setze auf Bekanntem auf, "
                "statt es zu wiederholen („Update:“ am Punktanfang, wenn ein Thema aus "
                "„Heute bereits berichtet“ weitergeht). 1–2 Punkte sind normal; Ruhige "
                "Lage ist erlaubt."
            ),
            "abend": (
                "**20:00 — Einordnung und Ausblick auf morgen.** Der Leser will den "
                "Tag abschließen. Nimm die wichtigste(n) Entwicklung(en) des Tages — "
                "auch aus „Heute bereits berichtet“ — und ordne sie ein: Was bedeutet "
                "das unterm Strich, was ist offen? Neue Meldungen seit 16 Uhr haben "
                "Vorrang, wenn sie die Schwelle erreichen. Schließe jeden Punkt, wo "
                "möglich, mit **Was kommt:** — mit Blick auf morgen. Keine Nacherzählung "
                "des ganzen Tages: höchstens 3 Punkte."
            ),
        },
        "bisher_heute_heading": "## Heute bereits berichtet (nicht wiederholen)",
        "termine_morgen_heading": "## Termine morgen (für den Ausblick)",
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
        "zweck_heading": "## Purpose of this edition",
        "zweck": {
            "morgen": (
                "**06:00 — Overview.** The reader is starting his day and has read "
                "nothing since last evening. Give the overview: what changed materially "
                "overnight and since last evening, what will shape today? Up to 5 points "
                "are normal only in this edition."
            ),
            "mittag": (
                "**11:00 — only what's new since the morning.** The reader knows the "
                "06:00 edition. Cover only what is new since then or has materially "
                "moved. Repeat nothing from \"Already covered today\" unless there is a "
                "genuinely new state — then start the point with \"Update:\". 1–2 points "
                "are normal; if nothing substantial came in, it's a quiet day."
            ),
            "nachmittag": (
                "**16:00 — Update.** What moved since midday: new decisions, numbers, "
                "reactions with consequences? Build on what's known instead of repeating "
                "it (\"Update:\" at the start when a topic from \"Already covered "
                "today\" continues). 1–2 points are normal; a quiet day is allowed."
            ),
            "abend": (
                "**20:00 — Context and a look ahead to tomorrow.** The reader wants to "
                "close the day. Take the day's most important development(s) — also from "
                "\"Already covered today\" — and put them in context: what does it mean "
                "on balance, what is still open? News since 16:00 takes priority if it "
                "clears the bar. End each point, where possible, with **What's next:** — "
                "looking to tomorrow. No retelling of the whole day: at most 3 points."
            ),
        },
        "bisher_heute_heading": "## Already covered today (do not repeat)",
        "termine_morgen_heading": "## Scheduled tomorrow (for the look ahead)",
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
