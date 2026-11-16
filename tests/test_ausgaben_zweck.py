"""Ausgaben-Zweck, Zeichen-Hygiene, Reifegrad-Gate, Feedback-Platzierung."""
from datetime import date, timedelta

from copilot import qualitaet, render, synthesize, webview


# ── 1a: Fremdzeichen ─────────────────────────────────────────────────────────

def test_braille_zeichen_wird_entfernt():
    assert qualitaet.bereinige_zeichen("<p>⣣ EU-Staaten starten") == "<p>EU-Staaten starten"
    assert qualitaet.bereinige_zeichen("Wien⣣ und Graz") == "Wien und Graz"


def test_emojis_keycaps_umlaute_bleiben():
    text = "1️⃣ 🏛 Öl „teurer“ — ✓ 👍🏽 👨‍👩‍👧 ⚖️\n  - eingerückt"
    assert qualitaet.bereinige_zeichen(text) == text


def test_cjk_pua_und_replacement_char_raus():
    assert qualitaet.bereinige_zeichen("Zins� steigt 中文") == "Zins steigt "


def test_webview_filtert_auch_archiv():
    body = webview._enhance_content(
        '<div class="highlights"><p><strong>Heute wichtig:</strong></p>\n  <p>⣣ EU-Staaten</p></div><hr>'
    )
    assert "⣣" not in body and "EU-Staaten" in body


# ── 1b: Feedback-Knöpfe nicht im eingeklappten Prüf-Block ────────────────────

LAGEBILD = """# 🌆 Dein Lagebild — Freitag

**Heute wichtig:**
1️⃣ Reform beschlossen

---

## 1️⃣ 🏠 Mietrechtsreform beschlossen
**Was ist neu:** Der Nationalrat hat entschieden.

## 2️⃣ 📊 EZB senkt den Leitzins
**Was ist neu:** Minus 25 Basispunkte.

## 🔍 Geprüft, nicht aufgenommen
- Ladenöffnungszeiten — betrifft dich kaum

🔍 *62 Meldungen geprüft* · 2 aufgenommen.

---
✅ *Du bist informiert — Lesezeit ca. 90 Sekunden.*
"""


def test_feedback_des_letzten_artikels_vor_pruefblock(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", tmp_path)
    _, html_path = render.write_output(LAGEBILD, "abend", "de")
    body = webview._extract_body(html_path.read_text(encoding="utf-8"), "2026-07-24", "abend", "de")
    assert body.count('class="article-fb"') == 2
    letzter = body.rfind('class="article-fb"')
    assert letzter < body.find('class="geprueft"') < body.find('class="pruef-head"')
    # Der Block „Geprüft, nicht aufgenommen" selbst bekommt keine Knöpfe.
    assert 'class="article-fb"' not in body[body.find('class="pruef-head"'):]


def test_feedback_endet_auch_vor_themen_kopf():
    html = (
        "<h2>EZB senkt</h2><p>Text</p>"
        '<h2 class="topic-summary-head">Deine Themen</h2><ul><li>x</li></ul><hr>'
    )
    out = webview._add_article_feedback(html, "2026-07-24", "abend")
    assert out.find('class="article-fb"') < out.find("topic-summary-head")


# ── 2: Reifegrad nur bei Regelungen ──────────────────────────────────────────

MD_RG = """**Heute wichtig:**
1️⃣ a

---

## 1️⃣ 🏛 Mietrechtsreform beschlossen
**Was ist neu:** Der Nationalrat hat das Gesetz beschlossen.
**Reifegrad:** Gilt ab 01.10.

## 2️⃣ 🌍 Raketenangriff auf Kiew
**Was ist neu:** Bei einem Angriff gab es zwölf Tote, die Regierung verurteilt ihn.
**Reifegrad:** Beschlossen

## 3️⃣ 🚇 Sperre auf der A23
**Was ist neu:** Stau nach Bauarbeiten.
**Reifegrad:** Ereignis

---
✅ fertig
"""


def test_reifegrad_bleibt_bei_regelung_und_faellt_bei_ereignis():
    out, n = qualitaet.entferne_reifegrad_bei_ereignissen(MD_RG)
    assert n == 2
    assert "**Reifegrad:** Gilt ab 01.10." in out
    assert "Beschlossen" not in out.split("Raketenangriff")[1]
    assert "Ereignis" not in out
    assert out.endswith("✅ fertig\n")


def test_reifegrad_ohne_zeile_ist_no_op():
    md = "## 1️⃣ 🌍 Unfall\n**Was ist neu:** Zwei Verletzte.\n"
    assert qualitaet.entferne_reifegrad_bei_ereignissen(md) == (md, 0)


# ── 3: Zweck je Ausgabe ──────────────────────────────────────────────────────

class _A:
    ressort, title, teaser, link, author, fulltext, published = (
        "Politik", "Titel", "Teaser", "", None, None, None,
    )


def test_jede_ausgabe_hat_eigenen_zweck():
    zwecke = {
        e: synthesize.build_prompt([_A()], [], "X", edition=e)
        for e in ("morgen", "mittag", "nachmittag", "abend")
    }
    assert "06:00 — Überblick" in zwecke["morgen"]
    assert "11:00 — nur Neues seit dem Morgen" in zwecke["mittag"]
    assert "16:00 — Update" in zwecke["nachmittag"]
    assert "20:00 — Einordnung und Ausblick auf morgen" in zwecke["abend"]
    for p in zwecke.values():
        assert "{AUSGABE_ZWECK}" not in p
        assert "Fülle niemals auf 3 auf" in p
        assert "Ruhige Lage" in p


def test_ohne_edition_kein_platzhalter_und_kein_zweck():
    prompt = synthesize.build_prompt([_A()], [], "Catch-up")
    assert "{AUSGABE_ZWECK}" not in prompt
    assert "## Zweck dieser Ausgabe" not in prompt


def test_spaetere_ausgaben_kennen_heute_berichtetes_und_abend_termine():
    morgen = (date.today() + timedelta(days=1)).isoformat()
    zweck = synthesize.ausgabe_zweck(
        "abend", "de", termine=[{"datum": morgen, "name": "EZB-Zinsentscheid"}],
        bisher_heute=["EZB senkt den Leitzins"],
    )
    assert "Heute bereits berichtet" in zweck and "- EZB senkt den Leitzins" in zweck
    assert "Termine morgen" in zweck and "EZB-Zinsentscheid" in zweck
    # Morgens gibt es nichts „bereits Berichtetes"
    assert "bereits berichtet" not in synthesize.ausgabe_zweck("morgen", bisher_heute=["x"])


def test_englischer_prompt_hat_zweck():
    p = synthesize.build_prompt([_A()], [], "X", edition="mittag", lang="en",
                                prompt_file="lagebild.en.md")
    assert "11:00 — only what's new since the morning" in p
    assert "Never pad to 3" in p


def test_bisher_heute_aus_state(monkeypatch):
    from datetime import datetime
    from copilot import main
    heute = f"{datetime.now():%Y-%m-%d}"
    st = {"edition_points": {f"{heute}|morgen": ["A", "B"], f"{heute}|mittag": ["B", "C"],
                             "2000-01-01|morgen": ["alt"]}}
    order = ["morgen", "mittag", "nachmittag", "abend"]
    assert main._bisher_heute(st, "nachmittag", order) == ["A", "B", "C"]
    assert main._bisher_heute(st, "morgen", order) == []


def test_webview_entfernt_reifegrad_bei_ereignis_auch_im_archiv():
    html = (
        "<h2>Frachtschiff nach Drohnenangriff gekentert</h2>"
        "<p><strong>Was ist neu:</strong> Ein Drohnenangriff, zwei Tote.</p>"
        '<p class="reifegrad"><span class="rg rg-gilt">Gilt ab 16.11</span></p>'
        "<h2>Nationalrat beschließt Mietpreisbremse</h2>"
        "<p><strong>Was ist neu:</strong> Das Gesetz ist beschlossen.</p>"
        "<p><strong>Reifegrad:</strong> Gilt ab 01.01.</p><hr>"
    )
    out = webview._enhance_neu(html, "de")
    assert "Gilt ab 16.11" not in out
    assert '<span class="rg rg-gilt">Gilt ab 01.01</span>' in out
