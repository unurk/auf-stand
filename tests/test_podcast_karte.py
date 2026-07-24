"""Podcast-Feed und teilbare Punkt-Karte."""
from datetime import date
from xml.etree import ElementTree

from copilot import karte, podcast

LAGEBILD = """# 🌆 Dein Lagebild — Freitag

**Heute wichtig:**
1️⃣ Reform beschlossen

---

## 1️⃣ 🏠 Mietrechtsreform im Nationalrat beschlossen
**Was ist neu:** Der Nationalrat hat die Reform beschlossen. Die Richtwerte werden gedeckelt. Ein dritter Satz.
**Warum es zählt:** Für Mieter sinkt die Erhöhung.
**Reifegrad:** Gilt ab 01.10.

## 2️⃣ 📊 Zweiter Punkt
**Was ist neu:** Anderes Thema.
"""


def test_top_punkt_liest_titel_kern_und_reifegrad():
    punkt = karte.top_punkt(LAGEBILD)
    assert punkt["titel"] == "Mietrechtsreform im Nationalrat beschlossen"
    assert punkt["kern"].startswith("Der Nationalrat hat die Reform beschlossen.")
    assert "Ein dritter Satz" not in punkt["kern"]  # nur zwei Sätze auf der Karte
    assert punkt["reifegrad"] == "Gilt ab 01.10."


def test_top_punkt_ohne_punkte_ist_none():
    assert karte.top_punkt("# Nur eine Überschrift\nText.") is None


def test_karte_wird_gerendert(tmp_path):
    pfad = karte.karte_fuer_ausgabe(
        LAGEBILD, "abend", "Abend-Ausgabe", datum=date(2026, 7, 24), out_dir=tmp_path
    )
    assert pfad is not None and pfad.exists()
    assert pfad.name == "2026-07-24-abend-karte.png"
    assert pfad.stat().st_size > 5000  # es wurde wirklich gezeichnet


def test_feed_leer_ohne_audio(tmp_path):
    assert podcast.build_feed(tmp_path, tmp_path / "feed.xml", "https://example.org/") is None


def test_feed_enthaelt_episoden_neueste_zuerst(tmp_path):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    for name in ("2026-07-23-abend.mp3", "2026-07-24-morgen.mp3", "2026-07-24-abend.mp3"):
        (archiv / name).write_bytes(b"ID3" + b"\0" * 100)
    (archiv / "kaputt.mp3").write_bytes(b"x")  # wird ignoriert

    ziel = podcast.build_feed(archiv, tmp_path / "feed.xml", "https://example.org/app")
    assert ziel is not None
    root = ElementTree.parse(ziel).getroot()
    items = root.findall("./channel/item")
    assert len(items) == 3
    titel = [i.findtext("title") for i in items]
    assert "24. Juli · Abend-Ausgabe" in titel[0]
    assert "23. Juli" in titel[-1]
    enclosure = items[0].find("enclosure")
    assert enclosure.get("url") == "https://example.org/app/archiv/2026-07-24-abend.mp3"
    assert enclosure.get("type") == "audio/mpeg"
    assert int(enclosure.get("length")) > 0


def test_feed_englisch(tmp_path):
    archiv = tmp_path / "archiv"
    archiv.mkdir()
    (archiv / "2026-07-24-morgen.mp3").write_bytes(b"ID3" + b"\0" * 10)
    ziel = podcast.build_feed(archiv, tmp_path / "feed.xml", "https://example.org/", lang="en")
    root = ElementTree.parse(ziel).getroot()
    assert root.findtext("./channel/language") == "en-US"
    assert "Morning Edition" in root.findtext("./channel/item/title")
