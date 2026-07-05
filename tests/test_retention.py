"""Tests für die Retention-Mechanismen: Streak-Zeile und Abend-Cliffhanger."""
from datetime import date, timedelta

from copilot import render, vorausschau

FOOTER = "✅ *Du bist informiert — Lesezeit ca. 90 Sekunden. Nächste Ausgabe heute 11:00.*"
LAGEBILD = f"# Dein Lagebild\n\n## 1️⃣ Punkt\nText\n\n---\n{FOOTER}"


def test_insert_streak_ab_tag_zwei():
    out = render.insert_streak(LAGEBILD, 12)
    assert "Du bist informiert — 12. Tag in Folge — Lesezeit" in out


def test_insert_streak_tag_eins_ist_kein_streak():
    assert render.insert_streak(LAGEBILD, 1) == LAGEBILD
    assert render.insert_streak(LAGEBILD, 0) == LAGEBILD


def test_insert_streak_englisch():
    md = "# Briefing\n\n✅ *You're informed — reading time ca. 90 seconds.*"
    out = render.insert_streak(md, 5, lang="en")
    assert "You're informed — day 5 in a row" in out


def test_insert_before_footer_landet_ueber_der_schlusszeile():
    out = render.insert_before_footer(LAGEBILD, "🔭 *Morgen wichtig:* EZB-Zinsentscheid")
    lines = out.splitlines()
    idx = next(i for i, l in enumerate(lines) if "Morgen wichtig" in l)
    assert "Du bist informiert" in lines[idx + 2]  # Teaser + Leerzeile + Schlusszeile


def test_insert_before_footer_ohne_marker_ans_ende():
    out = render.insert_before_footer("# Nur Titel", "Block")
    assert out.endswith("Block")


def test_morgen_teaser_nur_fuer_morgen():
    morgen = (date.today() + timedelta(days=1)).isoformat()
    heute = date.today().isoformat()
    uebermorgen = (date.today() + timedelta(days=2)).isoformat()
    termine = [
        {"datum": heute, "name": "Heute-Termin"},
        {"datum": morgen, "name": "EZB-Ratssitzung · Zinsentscheid"},
        {"datum": uebermorgen, "name": "Später-Termin"},
    ]
    teaser = vorausschau.format_morgen_teaser(termine)
    assert "EZB-Ratssitzung" in teaser
    assert "Heute-Termin" not in teaser and "Später-Termin" not in teaser
    assert teaser.startswith("🔭")


def test_morgen_teaser_leer_ohne_termine():
    assert vorausschau.format_morgen_teaser([]) == ""
    gestern = (date.today() - timedelta(days=1)).isoformat()
    assert vorausschau.format_morgen_teaser([{"datum": gestern, "name": "Vorbei"}]) == ""
