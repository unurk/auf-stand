"""Privater Podcast-Feed: das Lagebild landet in Apple Podcasts, Spotify, CarPlay.

Die Audio-Version existiert bereits (tts.py), erreicht aber nur den Telegram-Chat.
Ein RSS-Feed mit <enclosure> öffnet ohne eigene App das gesamte Audio-Ökosystem —
und damit den natürlichsten Konsum-Moment des Produkts: die 90 Sekunden auf dem
Weg zur Arbeit, an denen niemand ein Display anschaut.

Der Feed ist bewusst kurz gehalten (letzte 20 Ausgaben) und trägt kein Archiv-
Versprechen: Er ist eine Zustellart, kein Katalog.
"""
from __future__ import annotations

import re
from datetime import date, datetime, time, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

from . import i18n

# Kuratierungszeiten (Wien) je Ausgabe — für eine plausible pubDate-Reihenfolge.
_EDITION_STUNDE = {"morgen": 6, "mittag": 11, "nachmittag": 16, "abend": 20}
_EDITION_LABEL = {
    "de": {
        "morgen": "Morgen-Ausgabe",
        "mittag": "Mittags-Ausgabe",
        "nachmittag": "Nachmittags-Ausgabe",
        "abend": "Abend-Ausgabe",
    },
    "en": {
        "morgen": "Morning Edition",
        "mittag": "Midday Edition",
        "nachmittag": "Afternoon Edition",
        "abend": "Evening Edition",
    },
}
_DATEI_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(morgen|mittag|nachmittag|abend)\.mp3$")

MAX_EPISODEN = 20


def _episoden(archiv_dir: Path) -> list[tuple[date, str, Path]]:
    """Alle mp3s im Archiv, neueste zuerst."""
    gefunden: list[tuple[date, str, Path]] = []
    if not archiv_dir.exists():
        return gefunden
    for mp3 in archiv_dir.glob("*.mp3"):
        m = _DATEI_RE.match(mp3.name)
        if not m:
            continue
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        gefunden.append((d, m.group(4), mp3))
    gefunden.sort(key=lambda e: (e[0], _EDITION_STUNDE.get(e[1], 0)), reverse=True)
    return gefunden[:MAX_EPISODEN]


def _pub_date(d: date, edition: str) -> str:
    stunde = _EDITION_STUNDE.get(edition, 6)
    dt = datetime.combine(d, time(hour=stunde), tzinfo=timezone.utc)
    return format_datetime(dt)


def _episode_titel(d: date, edition: str, lang: str) -> str:
    weekdays = i18n.t(lang, "weekdays")
    months = i18n.t(lang, "months")
    label = _EDITION_LABEL.get(lang, _EDITION_LABEL["de"]).get(edition, edition)
    if lang == "en":
        return f"{weekdays[d.weekday()]}, {months[d.month - 1]} {d.day} · {label}"
    return f"{weekdays[d.weekday()]}, {d.day}. {months[d.month - 1]} · {label}"


def build_feed(
    archiv_dir: Path,
    ziel: Path,
    site_url: str,
    lang: str = "de",
    archiv_pfad: str = "archiv/",
) -> Path | None:
    """Schreibt den Podcast-Feed. None, wenn es keine Audio-Ausgaben gibt."""
    episoden = _episoden(archiv_dir)
    if not episoden:
        return None

    base = site_url if site_url.endswith("/") else site_url + "/"
    titel = i18n.t(lang, "podcast_title")
    beschreibung = i18n.t(lang, "podcast_description")
    autor = i18n.t(lang, "podcast_author")
    sprache = "de-AT" if lang == "de" else "en-US"

    items: list[str] = []
    for d, edition, mp3 in episoden:
        url = f"{base}{archiv_pfad}{mp3.name}"
        groesse = mp3.stat().st_size
        items.append(
            "    <item>\n"
            f"      <title>{escape(_episode_titel(d, edition, lang))}</title>\n"
            f"      <guid isPermaLink=\"false\">{escape(mp3.stem)}</guid>\n"
            f"      <pubDate>{_pub_date(d, edition)}</pubDate>\n"
            f"      <link>{escape(base)}</link>\n"
            f"      <description>{escape(i18n.t(lang, 'podcast_subtitle'))}</description>\n"
            f"      <enclosure url=\"{escape(url)}\" length=\"{groesse}\" type=\"audio/mpeg\"/>\n"
            "    </item>"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">\n'
        "  <channel>\n"
        f"    <title>{escape(titel)}</title>\n"
        f"    <link>{escape(base)}</link>\n"
        f"    <language>{sprache}</language>\n"
        f"    <description>{escape(beschreibung)}</description>\n"
        f"    <itunes:author>{escape(autor)}</itunes:author>\n"
        f"    <itunes:summary>{escape(beschreibung)}</itunes:summary>\n"
        f"    <itunes:subtitle>{escape(i18n.t(lang, 'podcast_subtitle'))}</itunes:subtitle>\n"
        '    <itunes:category text="News"/>\n'
        "    <itunes:explicit>false</itunes:explicit>\n"
        f'    <itunes:image href="{escape(base)}icon-512.png"/>\n'
        f"{chr(10).join(items)}\n"
        "  </channel>\n"
        "</rss>\n"
    )
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(xml, encoding="utf-8")
    print(f"Podcast-Feed gebaut: {ziel} ({len(episoden)} Episode(n))")
    return ziel
