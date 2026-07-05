"""Tests für die TTS-Textaufbereitung: aus Lagebild-Markdown wird vorlesbare Prosa."""
from copilot import tts

LAGEBILD = """# ☀️ Dein Lagebild — Freitag, 4. Juli 2026

**Heute wichtig:**
1️⃣ Mietpreisbremse beschlossen
2️⃣ EZB senkt Leitzins

---

## 1️⃣ 🏠 Mietpreisbremse kommt
**Was ist neu:** Der Nationalrat hat die Deckelung beschlossen. [→ Artikel](https://example.com/a1)

---
📰 Zur Vertiefung: das [E-Paper](https://www.diepresse.com/epaper) der heutigen Ausgabe.
✅ *Du bist informiert — Lesezeit ca. 90 Sekunden. Nächste Ausgabe heute 11:00.*
"""


def test_to_speech_text():
    text = tts._to_speech_text(LAGEBILD)
    # Übersichtsblock („Heute wichtig") wird nicht doppelt vorgelesen
    assert "Heute wichtig" not in text
    assert "Mietpreisbremse beschlossen\n" not in text
    # Emoji, Links, URLs und E-Paper-Footer sind raus
    assert "☀️" not in text and "🏠" not in text
    assert "http" not in text and "E-Paper" not in text
    # Abschlusszeile auf den Kern reduziert
    assert "Du bist informiert." in text
    assert "Lesezeit" not in text
    # Inhalt bleibt
    assert "Der Nationalrat hat die Deckelung beschlossen." in text
    assert "Mietpreisbremse kommt." in text  # Überschrift als Satz


def test_chunks_haelt_limit_ein():
    para = "Satz. " * 100  # ~600 Zeichen
    text = "\n\n".join([para] * 10)
    chunks = tts._chunks(text, limit=2000)
    assert all(len(c) <= 2000 for c in chunks)
    assert sum(c.count("Satz.") for c in chunks) == 1000


def test_chunks_teilt_ueberlange_absaetze_satzweise():
    text = "Ein Satz! " * 500  # ein Absatz, ~5000 Zeichen
    chunks = tts._chunks(text.strip(), limit=1000)
    assert all(len(c) <= 1000 for c in chunks)
    assert sum(c.count("Ein Satz!") for c in chunks) == 500


def test_tts_configured_respektiert_hartes_aus(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    assert tts.tts_configured({"tts": {"enabled": False}}) is False
    assert tts.tts_configured({"tts": {"enabled": True}}) is True
    monkeypatch.delenv("OPENAI_API_KEY")
    assert tts.tts_configured({"tts": {"enabled": True}}) is False
