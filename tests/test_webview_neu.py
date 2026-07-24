"""Rendering der neuen Elemente: Reifegrad, Nachtrag, Prüf-Block, Teilen, Profil."""
import re

from copilot import render, webview

LAGEBILD = """# 🌆 Dein Lagebild — Freitag

**Heute wichtig:**
1️⃣ Reform beschlossen

---

## 1️⃣ 🏠 Mietrechtsreform beschlossen
**Was ist neu:** Der Nationalrat hat entschieden.
**Für dich konkret:** Deine Anhebung im Oktober entfällt.
**Reifegrad:** Gilt ab 01.10.

## 2️⃣ 📊 EZB senkt den Leitzins
**Was ist neu:** Minus 25 Basispunkte.
**Nachtrag:** Wir schrieben gestern von einer Pause — der Rat entschied anders.
**Reifegrad:** Gerücht

## 🔍 Geprüft, nicht aufgenommen
- Ladenöffnungszeiten — keine Entscheidung

🔍 *62 Meldungen geprüft* · 2 aufgenommen.

---
✅ *Du bist informiert — Lesezeit ca. 90 Sekunden.*
"""


def _body(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", tmp_path)
    _, html_path = render.write_output(LAGEBILD, "abend", "de")
    return webview._extract_body(html_path.read_text(encoding="utf-8"), "2026-07-24", "abend", "de")


def test_reifegrad_wird_zur_ampel(tmp_path, monkeypatch):
    body = _body(tmp_path, monkeypatch)
    assert '<span class="rg rg-gilt">Gilt ab 01.10</span>' in body
    assert '<span class="rg rg-geruecht">Gerücht</span>' in body


def test_reifegrad_klassen():
    assert webview._reifegrad_klasse("Gilt ab 01.10.") == "rg-gilt"
    assert webview._reifegrad_klasse("Beschlossen") == "rg-beschlossen"
    assert webview._reifegrad_klasse("Entwurf") == "rg-entwurf"
    assert webview._reifegrad_klasse("Gerücht") == "rg-geruecht"
    assert webview._reifegrad_klasse("Unfug") == "rg-beschlossen"  # sichere Vorgabe


def test_nachtrag_und_fuer_dich_bekommen_eigene_klassen(tmp_path, monkeypatch):
    body = _body(tmp_path, monkeypatch)
    assert '<p class="nachtrag">' in body
    assert '<p class="fuer-dich">' in body
    assert "Deine Anhebung im Oktober entfällt" in body


def test_pruefblock_und_zaehlzeile(tmp_path, monkeypatch):
    body = _body(tmp_path, monkeypatch)
    assert 'class="pruef-head"' in body
    assert '<p class="geprueft">' in body
    assert "62 Meldungen geprüft" in body
    # Der Zähler muss VOR dem Abschnitt stehen, sonst zieht ihn das Accordion
    # in den eingeklappten Body — der Beweis wäre dann unsichtbar.
    assert body.index('class="geprueft"') < body.index("pruef-head")


def test_keycap_emojis_verschwinden_beim_ersten_build(tmp_path, monkeypatch):
    """Regression: früher blieben 1️⃣/2️⃣ bis zum nächsten Site-Build stehen."""
    body = _body(tmp_path, monkeypatch)
    highlights = re.search(r'<div class="highlights">.*?</div>', body, re.DOTALL).group(0)
    assert not re.search(r"\d️?⃣", highlights)


def test_teilen_button_nur_erster_punkt_mit_karte(tmp_path, monkeypatch):
    body = _body(tmp_path, monkeypatch)
    assert body.count("share-btn") == 2  # zwei Punkte, kein Button am Prüf-Block
    assert body.count('data-karte="2026-07-24-abend-karte.png"') == 1


def test_done_box_bleibt_bei_mehrfachem_build_stabil(tmp_path, monkeypatch):
    """Regression: Der Build läuft über bereits gebrandete Dateien."""
    body = _body(tmp_path, monkeypatch)
    for _ in range(3):
        body = webview._enhance_content(body, "2026-07-24", "abend", "de")
    assert body.count('<span class="done-check">✓</span>') == 1


def test_erster_punkt_fuer_nachholliste(tmp_path, monkeypatch):
    body = _body(tmp_path, monkeypatch)
    assert webview._erster_punkt(body) == "Mietrechtsreform beschlossen"


def test_profil_section_rendert_alle_fragen():
    from copilot import profil
    html = webview._profil_section({"antworten": {"wohnen": "miete"}})
    assert html.count('class="prof-block"') == len(profil.FRAGEN)
    assert 'data-nur-wenn="kredit"' in html  # bedingte Frage
    assert 'data-key="wohnen" data-wert="miete">Miete</button>' in html.replace(
        'class="prof-opt selected" ', ""
    )
    assert "/profil" in html


def test_podcast_section_enthaelt_feed_url():
    html = webview._podcast_section("https://example.org/app")
    assert "https://example.org/app/feed.xml" in html


def test_ausgaben_script_liefert_liste(tmp_path):
    from datetime import date
    pfad = tmp_path / "2026-07-24-abend.html"
    pfad.write_text("<h2>Ein Punkt</h2>", encoding="utf-8")
    script = webview._ausgaben_script([((date(2026, 7, 24), 3, "abend"), pfad)], "de")
    assert "window.__AUSGABEN__" in script
    assert '"2026-07-24-abend"' in script
    assert "Ein Punkt" in script
    assert re.search(r"__AKTUELLE_AUSGABE__=\"2026-07-24-abend\"", script)
