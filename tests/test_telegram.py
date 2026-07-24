"""Tests für die Telegram-MarkdownV2-Konvertierung — bricht sie, bricht die Zustellung."""
from copilot import telegram


def test_headings_werden_fett():
    out = telegram._to_telegram_md("# Titel\n## Punkt 1")
    lines = out.splitlines()
    assert lines[0] == "*Titel*"
    assert lines[1] == "*Punkt 1*"


def test_trennlinie():
    assert telegram._to_telegram_md("---") == "—————————————"


def test_links_bleiben_klickbar():
    out = telegram._to_telegram_md("Siehe [→ Artikel](https://example.com/a?x=1)")
    assert "[→ Artikel](https://example.com/a?x=1)" in out


def test_bold_und_sonderzeichen():
    out = telegram._to_telegram_md("**Was ist neu:** Deckel bei 3.5 Prozent (fix)")
    # Bold-Span als Telegram-*, Sonderzeichen im Fließtext escapt
    assert out.startswith("*Was ist neu:*")
    assert "3\\.5" in out
    assert "\\(fix\\)" in out


def test_escape_escapt_alle_sonderzeichen():
    for ch in telegram._SPECIAL:
        assert telegram._escape(ch) == f"\\{ch}"


def test_split_kurzer_text_bleibt_ganz():
    assert telegram._split("hallo") == ["hallo"]


def test_split_teilt_an_absatzgrenzen():
    para = "x" * 1500
    text = "\n\n".join([para] * 4)  # ~6000 Zeichen
    chunks = telegram._split(text, limit=4000)
    assert len(chunks) == 2
    assert all(len(c) <= 4000 for c in chunks)
    # Kein Inhalt verloren
    assert "".join(chunks).count("x") == 6000


def test_feedback_keyboard_format():
    kb = telegram._feedback_keyboard("2026-07-04|morgen", ["Mietpreisbremse beschlossen"])
    rows = kb["inline_keyboard"]
    # Eine Artikel-Zeile + Ausgaben-Zeile + Lese-/Fehlt-Zeile
    assert len(rows) == 3
    assert rows[0][0]["callback_data"] == "artfb|2026-07-04|morgen|0|up"
    assert rows[1][0]["callback_data"] == "fb|2026-07-04|morgen|up"
    assert rows[2][0]["callback_data"] == "read|2026-07-04|morgen"
    assert rows[2][1]["callback_data"] == "fehlt|2026-07-04|morgen"
