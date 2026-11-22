"""Textqualität 22.11.: Tipp- und Grammatikfehler in Titeln und „Warum es zählt"."""
import json
from pathlib import Path

from copilot import main, qualitaet, synthesize

AUSGABE = """# ☀️ Hötere Belastungen für Pendler

**Heute wichtig:**
1️⃣ Alt

---

## 1️⃣ 🌍 Klimakonferenz drohen zu scheitern
**Was ist neu:** Die Verhandlungen stocken.
**Warum es zählt:** Für dich könnte Kosten weitergereicht werden. (Ausland · Bericht: A. B.)
[→ Artikel](https://www.diepresse.com/1/klima)

## 2️⃣ 📦 Auslandsdelivrung wird ab 2027 teurer
**Was ist neu:** Die Post erhöht Gebühren.
**Warum es zählt:** Pakete kosten 3 Euro mehr. (Wirtschaft)
[→ Artikel](https://www.diepresse.com/2/post)

---
"""

KORREKTUR = {
    "Hötere Belastungen für Pendler": "Höhere Belastungen für Pendler",
    "Klimakonferenz drohen zu scheitern": "Klimakonferenz droht zu scheitern",
    "Für dich könnte Kosten weitergereicht werden.": "Für dich könnten Kosten weitergereicht werden.",
    "Auslandsdelivrung wird ab 2027 teurer": "Auslandslieferung wird ab 2027 teurer",
}


def _fake_modell(monkeypatch, korrektur=KORREKTUR, roh=None):
    gesendet = []

    def fake_complete(prompt, config, max_tokens, anthropic_model=None):
        texte = json.loads(prompt[prompt.index("["):])
        gesendet.append(texte)
        return roh if roh is not None else json.dumps([korrektur.get(t, t) for t in texte],
                                                      ensure_ascii=False)
    monkeypatch.setattr(synthesize, "_provider_configured", lambda c: True)
    monkeypatch.setattr(synthesize, "_complete", fake_complete)
    return gesendet


def test_prompt_verlangt_fehlerfreies_deutsch():
    prompt = Path(synthesize.PROMPTS_DIR / "lagebild.md").read_text(encoding="utf-8")
    assert "Fehlerfreies Deutsch" in prompt
    assert "hötere" in prompt and "drohen zu scheitern" in prompt


def test_nur_titel_und_warum_zeilen_ohne_quelle_und_link(monkeypatch):
    gesendet = _fake_modell(monkeypatch)
    synthesize.korrigiere_rechtschreibung(AUSGABE, {}, "de")
    assert gesendet[0] == [
        "Hötere Belastungen für Pendler",
        "Klimakonferenz drohen zu scheitern",
        "Für dich könnte Kosten weitergereicht werden.",
        "Auslandsdelivrung wird ab 2027 teurer",
        "Pakete kosten 3 Euro mehr.",
    ]


def test_korrekturen_werden_uebernommen(monkeypatch):
    _fake_modell(monkeypatch)
    out, n = synthesize.korrigiere_rechtschreibung(AUSGABE, {}, "de")
    assert n == 4
    assert out.startswith("# ☀️ Höhere Belastungen für Pendler\n")
    assert "## 1️⃣ 🌍 Klimakonferenz droht zu scheitern" in out
    assert ("**Warum es zählt:** Für dich könnten Kosten weitergereicht werden. "
            "(Ausland · Bericht: A. B.)") in out
    assert "## 2️⃣ 📦 Auslandslieferung wird ab 2027 teurer" in out
    assert out.count("[→ Artikel](") == 2


def test_umschreiben_oder_zahlen_aendern_wird_verworfen(monkeypatch):
    _fake_modell(monkeypatch, korrektur={
        "Auslandsdelivrung wird ab 2027 teurer": "Auslandslieferung wird ab 2028 teurer",
        "Klimakonferenz drohen zu scheitern": "Weltklimagipfel in Belém steht vor dem Aus",
    })
    out, n = synthesize.korrigiere_rechtschreibung(AUSGABE, {}, "de")
    assert n == 0 and out == AUSGABE


def test_kaputte_antwort_ist_no_op(monkeypatch):
    _fake_modell(monkeypatch, roh="Leider kann ich das nicht.")
    assert synthesize.korrigiere_rechtschreibung(AUSGABE, {}, "de") == (AUSGABE, 0)
    _fake_modell(monkeypatch, roh='["nur eine Zeile"]')
    assert synthesize.korrigiere_rechtschreibung(AUSGABE, {}, "de") == (AUSGABE, 0)


def test_abschaltbar_und_nicht_fuer_englisch(monkeypatch):
    gesendet = _fake_modell(monkeypatch)
    assert synthesize.korrigiere_rechtschreibung(AUSGABE, {"rechtschreib_check": False}, "de")[1] == 0
    assert synthesize.korrigiere_rechtschreibung(AUSGABE, {}, "en")[1] == 0
    assert gesendet == []


def test_ohne_provider_kein_aufruf(monkeypatch):
    monkeypatch.setattr(synthesize, "_provider_configured", lambda c: False)
    monkeypatch.setattr(synthesize, "_complete",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("kein Aufruf")))
    assert synthesize.korrigiere_rechtschreibung(AUSGABE, {}, "de") == (AUSGABE, 0)


def test_heute_wichtig_uebernimmt_korrigierte_titel(monkeypatch):
    _fake_modell(monkeypatch)
    out = main._bereinige_modell_output(AUSGABE, "de", config={"provider": "anthropic"})
    assert "1️⃣ Klimakonferenz droht zu scheitern" in out
    assert "2️⃣ Auslandslieferung wird ab 2027 teurer" in out


def test_korrektur_zulaessig_grenzen():
    assert qualitaet.korrektur_zulaessig("hötere Kosten", "höhere Kosten")
    assert not qualitaet.korrektur_zulaessig("3 Euro", "4 Euro")
    assert not qualitaet.korrektur_zulaessig("Text", "")
    assert not qualitaet.korrektur_zulaessig("Text", "Text\nmehr")
