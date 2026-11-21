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


# ── Telegram-Ausgabe vom 20.11.: alle Punkte müssen ankommen ─────────────────

def _telegram_sichtbar(t: str) -> str:
    """Minimaler MarkdownV2-Parser wie bei Telegram: liefert den sichtbaren Text.

    Wirft bei unescapten Sonderzeichen oder offenen Entities — genau dann
    weist Telegram die ganze Nachricht ab.
    """
    out, i, offen = [], 0, []
    while i < len(t):
        c = t[i]
        if c == "\\":
            out.append(t[i + 1])
            i += 2
            continue
        if c in "*_~|":
            tok = t[i:i + 2] if t[i:i + 2] in ("__", "||") else c
            i += len(tok)
            if offen and offen[-1] == tok:
                offen.pop()
            else:
                offen.append(tok)
            continue
        if c == "[":
            j = t.index("](", i)
            k = t.index(")", j)
            out.append(_telegram_sichtbar(t[i + 1:j]))
            i = k + 1
            continue
        assert c not in ">#+-=|{}.!()`]", f"unescaptes {c!r}: {t[max(0, i - 20):i + 10]!r}"
        out.append(c)
        i += 1
    assert not offen, f"offene Entity {offen}"
    return "".join(out)


_AUSGABE_2011 = "\n".join(
    ["# ☀️ Ruanda-Pläne: Karner nennt erstmals konkretes Datum",
     "*Freitag, 20. November 2026 · Morgen-Ausgabe · Lesezeit ca. 165 Sekunden*", "",
     "**Heute wichtig:**",
     "1️⃣ Karner legt Zeitplan für Ruanda-Abschiebezentrum fest",
     "2️⃣ Steiermark steuert auf milliardenschweren Schuldenberg zu",
     "3️⃣ Mayr-Melnhof meldet bis zu 340 Mio. Euro Verlust",
     "4️⃣ Wien zieht Airbnb-Schraube auf eine Wohnung an",
     "5️⃣ SVS-Beiträge: Verpasste Frist kostet 18.632 Euro", "", "---", ""]
    + [
        f"## {n}️⃣ 📊 Punkt {n}\n**Was ist neu:** " + "Text mit Zahlen wie 3.5 % (Wien). " * 25
        + f"\n**Warum es zählt:** Folgen. (Wirtschaft · Bericht: A. B.)\n"
        f"[→ Artikel](https://www.diepresse.com/4147{n}/punkt-{n})\n"
        for n in range(1, 6)
    ]
    + ["---", "", "✓ Du bist informiert — Nächstes Lagebild: heute 11:00 Uhr."]
)


def test_ausgabe_mit_fuenf_punkten_kommt_vollstaendig_an():
    text = telegram._to_telegram_md(_AUSGABE_2011)
    teile = telegram._split(text)
    sichtbar = "\n\n".join(_telegram_sichtbar(t) for t in teile)
    for n, titel in enumerate(["Karner legt Zeitplan", "Steiermark steuert", "Mayr-Melnhof meldet",
                               "Wien zieht Airbnb", "SVS-Beiträge: Verpasste Frist"], 1):
        assert f"{n}️⃣ {titel}" in sichtbar
        assert f"Punkt {n}" in sichtbar
    assert all(telegram._sichtbare_laenge(t) <= 4096 for t in teile)


def test_split_zaehlt_sichtbare_zeichen_nicht_escapes():
    # 3000 sichtbare Zeichen, escapt aber 6000 — passt in EINE Telegram-Nachricht.
    text = "\\." * 3000
    assert len(text) == 6000
    assert telegram._split(text) == [text]


def test_split_zaehlt_emoji_wie_telegram_doppelt():
    assert telegram._sichtbare_laenge("📊") == 2
    assert telegram._sichtbare_laenge("ä\\-") == 2


def test_einzelnes_sternchen_bricht_nachricht_nicht():
    out = telegram._to_telegram_md("5️⃣ Preis * Leistung: Wer gewinnt?")
    assert _telegram_sichtbar(out) == "5️⃣ Preis * Leistung: Wer gewinnt?"
    # echte Kursiv-Spans bleiben Kursiv
    assert _telegram_sichtbar(telegram._to_telegram_md("Plan *A* oder B")) == "Plan A oder B"
