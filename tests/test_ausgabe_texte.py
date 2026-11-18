"""Text-Qualität der Ausgaben — Befunde aus der Morgen-Ausgabe vom 18.11.2026.

1) „Für dich als Konsumentin" — der Leser ist ein Mann.
2) „drohen store closures" — englische Einsprengsel im deutschen Text.
3) „Heute wichtig" passt nicht zu den Punkten darunter.
4) „Für dein politisches Verständnis:" — Meta-Floskel statt konkreter Folge.
"""
from pathlib import Path

from copilot import main, qualitaet, render, synthesize, webview

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"

AUSGABE = """# ☀️ Dein Lagebild — Mittwoch, 18. November 2026 · Morgen-Ausgabe

**Heute wichtig:**
1️⃣ Handels-KV: Streikbeschlüsse vor Weihnachtsgeschäft
2️⃣ EU hebt Wachstumsprognose an
3️⃣ Budgetdefizit sinkt nur scheinbar

---

## 1️⃣ 📊 Handels-KV: Streikbeschlüsse vor Weihnachtsgeschäft
**Was ist neu:** Nach der dritten Runde ohne Einigung stehen Betriebsversammlungen an.
**Warum es zählt:** Eskaliert der Konflikt, drohen store closures genau im Weihnachtsgeschäft. Für dich als Konsumentin bedeutet das Einschränkungen beim Einkauf.
(Wirtschaft) [→ Artikel](https://www.diepresse.com/1)

## 2️⃣ 🏛 Regierung einigt sich auf Entwurf zur Bundesstaatsanwaltschaft
**Warum es zählt:** Die Weisungsspitze bleibt neun Jahre. Für dein politisches Verständnis: Die Regierung braucht die Grünen für die Zweidrittelmehrheit.
**Reifegrad:** Entwurf

## 3️⃣ 📊 Euro auf 19-Monats-Tief — Dollar legt weiter zu
**Was ist neu:** Der Euro ist so günstig wie zuletzt vor 19 Monaten.

---
✅ *Du bist informiert — Lesezeit ca. 90 Sekunden.*
"""


# ── 3) „Heute wichtig" == Punkte, gleiche Reihenfolge ────────────────────────

def _heute_wichtig(md: str) -> list[str]:
    zeilen = md.split("**Heute wichtig:**", 1)[1].split("---", 1)[0].strip().splitlines()
    return [qualitaet._KEYCAP_PREFIX_RE.sub("", z).strip() for z in zeilen if z.strip()]


def test_punkt_titel_ohne_keycap_und_ressort_emoji():
    assert qualitaet.punkt_titel(AUSGABE) == [
        "Handels-KV: Streikbeschlüsse vor Weihnachtsgeschäft",
        "Regierung einigt sich auf Entwurf zur Bundesstaatsanwaltschaft",
        "Euro auf 19-Monats-Tief — Dollar legt weiter zu",
    ]


def test_heute_wichtig_wird_exakt_aus_den_punkten_gebaut():
    md, geaendert = qualitaet.synchronisiere_heute_wichtig(AUSGABE)
    assert geaendert
    assert _heute_wichtig(md) == qualitaet.punkt_titel(AUSGABE)
    assert "EU hebt Wachstumsprognose" not in md and "Budgetdefizit" not in md
    assert "1️⃣ Handels-KV" in md and "3️⃣ Euro auf 19-Monats-Tief" in md
    # Rest der Ausgabe unverändert
    assert md.split("---", 1)[1] == AUSGABE.split("---", 1)[1]


def test_heute_wichtig_mehr_punkte_als_zeilen_und_umgekehrt():
    zu_wenig = AUSGABE.replace("2️⃣ EU hebt Wachstumsprognose an\n3️⃣ Budgetdefizit sinkt nur scheinbar\n", "")
    md, _ = qualitaet.synchronisiere_heute_wichtig(zu_wenig)
    assert len(_heute_wichtig(md)) == 3
    zu_viele = AUSGABE.replace("3️⃣ Budgetdefizit", "3️⃣ X\n4️⃣ Y\n5️⃣ Budgetdefizit")
    md, _ = qualitaet.synchronisiere_heute_wichtig(zu_viele)
    assert len(_heute_wichtig(md)) == 3


def test_heute_wichtig_idempotent():
    md, _ = qualitaet.synchronisiere_heute_wichtig(AUSGABE)
    assert qualitaet.synchronisiere_heute_wichtig(md) == (md, False)


def test_ruhige_lage_bleibt_unangetastet():
    ruhig = "**Heute wichtig:**\nRuhige Lage — kein Handlungsbedarf.\n\n---\n\nNichts bewegt.\n"
    assert qualitaet.synchronisiere_heute_wichtig(ruhig) == (ruhig, False)


def test_web_rendering_behaelt_ziffern_in_heute_wichtig(tmp_path, monkeypatch):
    """Bug 18.11.: „Euro auf 19-Monats-Tief" wurde zu „Euro auf -Monats-Tief"."""
    monkeypatch.setattr(render, "OUT_DIR", tmp_path)
    md, _ = qualitaet.synchronisiere_heute_wichtig(AUSGABE)
    _, html_path = render.write_output(md, "morgen", "de")
    body = webview._extract_body(html_path.read_text(encoding="utf-8"), "2026-11-18", "morgen", "de")
    box = body.split('<div class="highlights">', 1)[1].split("</div>", 1)[0]
    assert "Euro auf 19-Monats-Tief" in box
    assert "⃣" not in box  # Keycaps weiterhin entfernt


# ── 2) Sprache: durchgehend Deutsch ──────────────────────────────────────────

def test_store_closures_wird_erkannt():
    assert qualitaet.finde_englisch("Es drohen store closures im Handel.") == ["store", "closures"]


def test_store_closures_wird_ersetzt():
    md, n = qualitaet.ersetze_anglizismen("Es drohen store closures im Handel.")
    assert md == "Es drohen Geschäftsschließungen im Handel." and n == 1
    assert qualitaet.finde_englisch(md) == []


def test_englische_endungen_werden_erkannt():
    assert "bookings" in qualitaet.finde_englisch("Die bookings brechen ein.")
    assert "negotiations" in qualitaet.finde_englisch("Die negotiations laufen.")


def test_keine_fehlalarme_bei_deutschem_text():
    deutsch = (
        "Allerdings will die Regierung das Budget neuerdings kürzen. Der Deal mit dem "
        "Team ist ein Job für Manager. Was war, ist vorbei — also bleibt die Inflation hoch. "
        "Die Not ist groß, die Rate steigt."
    )
    assert qualitaet.finde_englisch(deutsch) == []


def test_englisch_in_links_zitaten_und_quellen_ist_erlaubt():
    md = (
        'Das Buch „The Art of the Deal“ und "Breaking the Rules" (Politik · Bericht: '
        "John the Smith) [→ the article](https://diepresse.com/the-store-closures)"
    )
    assert qualitaet.finde_englisch(md) == []


def test_pipeline_ersetzt_ohne_modell_aufruf():
    out = main._bereinige_modell_output(AUSGABE, "de", config=None)
    assert "store closures" not in out and "Geschäftsschließungen" in out


def test_restliches_englisch_loest_einen_korrektur_durchlauf_aus(monkeypatch):
    md = AUSGABE.replace("drohen store closures", "drohen the shutdowns")
    aufrufe = []

    def fake_korrektur(text, woerter, config):
        aufrufe.append(woerter)
        return text.replace("the shutdowns", "Betriebsstillstände")

    monkeypatch.setattr(synthesize, "korrigiere_sprache", fake_korrektur)
    out = main._bereinige_modell_output(md, "de", config={"provider": "anthropic"})
    assert aufrufe and "the" in aufrufe[0] and "shutdowns" in aufrufe[0]
    assert "Betriebsstillstände" in out and qualitaet.finde_englisch(out) == []


def test_kein_korrektur_durchlauf_ohne_englisch(monkeypatch):
    md = AUSGABE.replace("store closures", "Schließungen")
    monkeypatch.setattr(synthesize, "korrigiere_sprache",
                        lambda *a: (_ for _ in ()).throw(AssertionError("unnötig")))
    main._bereinige_modell_output(md, "de", config={"provider": "anthropic"})


def test_korrektur_wird_verworfen_wenn_struktur_bricht(monkeypatch):
    monkeypatch.setattr(synthesize, "_provider_configured", lambda c: True)
    monkeypatch.setattr(synthesize, "_complete", lambda *a, **k: "Kaputt, ohne Punkte.")
    assert synthesize.korrigiere_sprache(AUSGABE, ["store"], {}) == AUSGABE


def test_korrektur_wird_uebernommen_wenn_struktur_bleibt(monkeypatch):
    monkeypatch.setattr(synthesize, "_provider_configured", lambda c: True)
    monkeypatch.setattr(synthesize, "_complete",
                        lambda *a, **k: AUSGABE.replace("store closures", "Ladenschließungen"))
    out = synthesize.korrigiere_sprache(AUSGABE, ["store", "closures"], {})
    assert "Ladenschließungen" in out


def test_englische_ausgabe_wird_nicht_geprueft(monkeypatch):
    monkeypatch.setattr(synthesize, "korrigiere_sprache",
                        lambda *a: (_ for _ in ()).throw(AssertionError("nicht für en")))
    out = main._bereinige_modell_output("## 1️⃣ 🏛 The store closures\nText.\n", "en", {})
    assert "store closures" in out


# ── 1) Anrede und 4) Floskeln ────────────────────────────────────────────────

def test_keine_weibliche_rollenbezeichnung_fuer_den_leser():
    md, n = qualitaet.neutralisiere_anrede(
        "Für dich als Konsumentin, für dich als Mieterin, dir als Konsument:in, du als Kundin."
    )
    assert md == "Für dich als Konsument, für dich als Mieter, dir als Konsument, du als Kunde."
    assert n == 4


def test_andere_weibliche_formen_bleiben():
    text = "Die Ministerin und die Leiterin der Behörde."
    assert qualitaet.neutralisiere_anrede(text) == (text, 0)


def test_meta_floskel_wird_entfernt():
    md, n = qualitaet.entferne_meta_floskeln(
        "Die Spitze bleibt neun Jahre. Für dein politisches Verständnis: Die Regierung braucht die Grünen."
    )
    assert md == "Die Spitze bleibt neun Jahre. Die Regierung braucht die Grünen." and n == 1


def test_pipeline_gesamt_18_11():
    out = main._bereinige_modell_output(AUSGABE, "de", config=None)
    assert "Konsumentin" not in out
    assert "politisches Verständnis" not in out
    assert _heute_wichtig(out) == qualitaet.punkt_titel(out)


# ── Prompt ───────────────────────────────────────────────────────────────────

def test_prompt_regeln():
    de = (PROMPTS / "lagebild.md").read_text(encoding="utf-8")
    assert "Leserin" not in de
    assert "durchgehend Deutsch" in de
    assert "„Heute wichtig\" spiegelt die Punkte exakt" in de
    assert "Für dein politisches Verständnis:" in de  # nur als Verbot
    assert "politische Verständnis der" not in de
    en = (PROMPTS / "lagebild.en.md").read_text(encoding="utf-8")
    assert " She " not in en and " her " not in en
