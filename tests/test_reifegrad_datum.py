"""„Gilt ab" nur mit echtem Datum — der Format-Platzhalter darf nie als Badge erscheinen.

Anlass: Morgen-Ausgabe 17.11.2026, „Wiener Regeln: Home-Sharing nur noch für eine
Wohnung" trug das Badge „Gilt ab TT.MM".
"""
from pathlib import Path

import pytest

from copilot import main, qualitaet, render, webview

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


# ── normalisiere_reifegrad ───────────────────────────────────────────────────

@pytest.mark.parametrize("wert", [
    "Gilt ab TT.MM", "Gilt ab TT.MM.", "Gilt ab DD.MM.", "Gilt ab TT.MM.JJJJ",
    "Gilt ab", "gilt ab Datum",
])
def test_platzhalter_ohne_datum_faellt_auf_beschlossen(wert):
    assert qualitaet.normalisiere_reifegrad(wert) == "Beschlossen"


@pytest.mark.parametrize("wert", [
    "Gilt ab 17.11.", "Gilt ab 17.11", "Gilt ab 1.1.2027", "Gilt ab 01.10.26",
    "Gilt ab 1. Jänner 2027", "Gilt ab 17. November", "Gilt ab Jänner 2027",
])
def test_echtes_datum_bleibt(wert):
    assert qualitaet.normalisiere_reifegrad(wert) == wert


@pytest.mark.parametrize("wert", ["Gerücht", "Entwurf", "Beschlossen", "In Kraft"])
def test_andere_stufen_unveraendert(wert):
    assert qualitaet.normalisiere_reifegrad(wert) == wert


def test_englisch():
    assert qualitaet.normalisiere_reifegrad("Effective MM/DD", "en") == "Decided"
    assert qualitaet.normalisiere_reifegrad("Effective DD/MM", "en") == "Decided"
    for ok in ("Effective 11/17", "Effective Jan. 1, 2027", "Effective November 17"):
        assert qualitaet.normalisiere_reifegrad(ok, "en") == ok


# ── Gate nach der Synthese (Markdown) ────────────────────────────────────────

MD = """## 1️⃣ 🏠 Wiener Regeln: Home-Sharing nur noch für eine Wohnung
**Was ist neu:** Der Landtag hat die Novelle beschlossen.
**Reifegrad:** Gilt ab TT.MM

## 2️⃣ 🏛 Mietpreisbremse
**Was ist neu:** Der Nationalrat hat das Gesetz beschlossen.
**Reifegrad:** Gilt ab 17.11.

---
"""


def test_markdown_gate_exakt_gilt_ab_tt_mm():
    out, n = qualitaet.korrigiere_reifegrad_platzhalter(MD)
    assert n == 1
    assert "TT.MM" not in out
    assert "**Reifegrad:** Beschlossen" in out
    assert "**Reifegrad:** Gilt ab 17.11." in out


def test_markdown_gate_englisch():
    md = "## 1️⃣ 🏛 Rule\n**Status:** Effective MM/DD\n"
    out, n = qualitaet.korrigiere_reifegrad_platzhalter(md, "en")
    assert (out, n) == ("## 1️⃣ 🏛 Rule\n**Status:** Decided\n", 1)


def test_pipeline_nachbearbeitung_greift():
    out = main._bereinige_modell_output(MD, "de")
    assert "TT.MM" not in out and "Gilt ab 17.11." in out


# ── Web-Rendering (frisch und Archiv) ────────────────────────────────────────

def test_web_rendering_frische_ausgabe(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", tmp_path)
    md = "# ☀️ Dein Lagebild\n\n**Heute wichtig:**\n1️⃣ x\n\n---\n\n" + MD + "✅ *Du bist informiert.*\n"
    _, html_path = render.write_output(md, "morgen", "de")
    body = webview._extract_body(html_path.read_text(encoding="utf-8"), "2026-11-17", "morgen", "de")
    assert "TT.MM" not in body
    assert '<span class="rg rg-beschlossen">Beschlossen</span>' in body
    assert '<span class="rg rg-gilt">Gilt ab 17.11</span>' in body


def test_web_rendering_archiv_badge_wird_korrigiert():
    html = (
        "<h2>Wiener Regeln: Home-Sharing nur noch für eine Wohnung</h2>"
        "<p><strong>Was ist neu:</strong> Der Landtag hat die Novelle beschlossen.</p>"
        '<p class="reifegrad"><span class="rg rg-gilt">Gilt ab TT.MM</span></p>'
        "<h2>Mietpreisbremse</h2><p>Das Gesetz ist beschlossen.</p>"
        '<p class="reifegrad"><span class="rg rg-gilt">Gilt ab 17.11</span></p><hr>'
    )
    out = webview._enhance_neu(html, "de")
    assert "TT.MM" not in out
    assert '<span class="rg rg-beschlossen">Beschlossen</span>' in out
    assert '<span class="rg rg-gilt">Gilt ab 17.11</span>' in out
    assert webview._enhance_neu(out, "de") == out  # idempotent


def test_archiv_17_11_morgen():
    pfad = Path(__file__).resolve().parent.parent / "site/archiv/2026-11-17-morgen.html"
    if not pfad.exists():
        pytest.skip("Archiv-Datei nicht vorhanden")
    body = webview._extract_body(pfad.read_text(encoding="utf-8"), "2026-11-17", "morgen", "de")
    assert "TT.MM" not in body


# ── Prompt ───────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("datei, platzhalter", [
    ("lagebild.md", ("TT.MM", "DD.MM")), ("lagebild.en.md", ("MM/DD", "DD.MM")),
])
def test_prompt_nennt_platzhalter_nur_im_verbot(datei, platzhalter):
    text = (PROMPTS / datei).read_text(encoding="utf-8")
    for p in platzhalter:
        zeilen = [z for z in text.splitlines() if p in z]
        assert len(zeilen) == 1, (p, zeilen)
        assert "nie" in zeilen[0].lower() or "never" in zeilen[0].lower()
