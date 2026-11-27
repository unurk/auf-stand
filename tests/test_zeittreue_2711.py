"""Regression 27.11.: „ab Montag" bei Datum 1. Dezember (Dienstag) und
„Hattmannsdorfer beendet Margeneingriff" bei „will … auslaufen lassen"."""
from datetime import date

from copilot import main, titelcheck, zeittreue
from copilot.fetch import Article

FREITAG = date(2026, 11, 27)
QUELLE = Article(
    id="1", title="Spritpreisbremse: Hattmannsdorfer für Auslaufen des Margeneingriffs",
    teaser="", ressort="Wirtschaft", published=None,
    link="https://www.diepresse.com/41495014/spritpreisbremse-hattmannsdorfer-fuer-auslaufen-des-margeneingriffs",
)
AUSGABE = """# ☀️ Spritpreisbremse: Hattmannsdorfer beendet Margeneingriff
*Freitag, 27. November 2026 · Morgen-Ausgabe*

**Heute wichtig:**
1️⃣ Spritpreisbremse: Hattmannsdorfer beendet Margeneingriff
2️⃣ Flugabgabe: Senkung in Aussicht, aber keine Streichung

---

## 1️⃣ ⛽ Spritpreisbremse: Hattmannsdorfer beendet Margeneingriff
**Was ist neu:** Wirtschaftsminister Wolfgang Hattmannsdorfer will die Margenbegrenzung bei den Spritpreisen Ende November auslaufen lassen. Ab 1. Dezember soll die Spritpreisbremse nur noch über die Mineralölsteuer wirken.
**Warum es zählt:** Wenn du autofährst, musst du ab Montag mit spürbar anderen Tankpreisen rechnen. (Wirtschaft)
**Reifegrad:** Gilt ab 1.12
[→ Artikel](https://www.diepresse.com/41495014/spritpreisbremse-hattmannsdorfer-fuer-auslaufen-des-margeneingriffs)

## 2️⃣ ✈️ Flugabgabe: Senkung in Aussicht, aber keine Streichung
**Was ist neu:** Verkehrsminister Peter Hanke stellt eine Senkung der umstrittenen Flugabgabe in Aussicht.
**Warum es zählt:** Eine Senkung würde Flugreisen aus Wien günstiger machen. (Wirtschaft)
[→ Artikel](https://www.diepresse.com/41495872/hanke-stellt-senkung-der-flugabgabe-in-aussicht)

---
"""


def test_fall_27_11_ende_zu_ende():
    out = main._pruefe_titel(AUSGABE, [QUELLE], heute=FREITAG)
    # 1) Wochentag: 1.12.2026 ist ein Dienstag → „ab Montag" wird zum Datum
    assert "musst du ab 1. Dezember mit spürbar anderen Tankpreisen rechnen" in out
    assert "ab Montag" not in out
    # 2) Absicht: Titel, H1 und „Heute wichtig" tragen die Quell-Schlagzeile
    neu = "Spritpreisbremse: Hattmannsdorfer für Auslaufen des Margeneingriffs"
    assert f"## 1️⃣ ⛽ {neu}" in out
    assert out.startswith(f"# ☀️ {neu}\n")
    assert f"1️⃣ {neu}\n" in out
    assert "beendet" not in out
    # Punkt 2 (Absicht schon im Titel: „in Aussicht") bleibt
    assert "## 2️⃣ ✈️ Flugabgabe: Senkung in Aussicht, aber keine Streichung" in out


def test_absicht_ohne_quelle_bekommt_geplant():
    out, k = titelcheck.pruefe_titel(AUSGABE, [])
    assert "## 1️⃣ ⛽ Geplant: Spritpreisbremse: Hattmannsdorfer beendet Margeneingriff" in out
    assert out.startswith("# ☀️ Geplant: Spritpreisbremse")
    assert any("Absicht" in x for x in k)


def test_vollzug_wird_nicht_als_absicht_gewertet():
    md = AUSGABE.replace(
        "Wirtschaftsminister Wolfgang Hattmannsdorfer will die Margenbegrenzung bei den "
        "Spritpreisen Ende November auslaufen lassen.",
        "Der Ministerrat hat beschlossen, die Margenbegrenzung Ende November auslaufen zu lassen.")
    out, k = titelcheck.pruefe_titel(md, [QUELLE])
    assert not any("Absicht" in x for x in k)
    assert "## 1️⃣ ⛽ Spritpreisbremse: Hattmannsdorfer beendet Margeneingriff" in out


# ── Wochentage: Gegenproben aus dem Archiv ──────────────────────────────────

def _punkt(titel, text):
    return f"## 1️⃣ 📊 {titel}\n**Was ist neu:** {text}\n"


def test_passender_wochentag_bleibt():
    md = _punkt("Spritpreisbremse", "Ab 1. Dezember wirkt nur noch die Steuer, also ab Dienstag.")
    assert zeittreue.pruefe_wochentage(md, FREITAG) == (md, [])


def test_ab_morgen_bei_datum_in_vier_tagen():
    # 3.7.2026 (Freitag): Titel „ab morgen", Text „Ab dem 7. Juli" (Dienstag)
    md = _punkt("Neue EU-Sicherheitsstandards für Neuwagen ab morgen",
                "Ab dem 7. Juli müssen alle neu zugelassenen Fahrzeuge Assistenzsysteme haben.")
    out, k = zeittreue.pruefe_wochentage(md, date(2026, 7, 3))
    assert "Neuwagen ab 7. Juli" in out and k


def test_montag_an_einem_montag_meint_heute():
    # 3.8.2026 (Montag): „U4 fährt ab Montag wieder", „Gilt ab 03.08"
    md = _punkt("Wiens U4 fährt ab Montag wieder durchgehend", "Die Bauarbeiten enden.") + "Gilt ab 03.08\n"
    assert zeittreue.pruefe_wochentage(md, date(2026, 8, 3)) == (md, [])


def test_fernes_datum_ist_kein_bezug():
    # 7.10.2026: „bis Donnerstag" = Einreichfrist, „Gilt ab 01.01.2027" = etwas anderes
    md = _punkt("Letzte Solarförderung nach alten Regeln",
                "Wer plant, muss bis Donnerstag einreichen.") + "Gilt ab 01.01.2027\n"
    assert zeittreue.pruefe_wochentage(md, date(2026, 10, 7)) == (md, [])


def test_mehrere_daten_ohne_treffer_streicht_die_angabe():
    md = _punkt("Fristen", "Ab 1. Dezember gilt A, ab 3. Dezember gilt B — und das ab Montag.")
    out, k = zeittreue.pruefe_wochentage(md, FREITAG)
    assert "ab Montag" not in out and "und das." in out and k


def test_ohne_datum_nichts_pruefbar():
    md = _punkt("Streik", "Die Gewerkschaft streikt ab Montag.")
    assert zeittreue.pruefe_wochentage(md, FREITAG) == (md, [])


def test_zahl_mit_punkt_ist_kein_datum():
    assert zeittreue.daten("Die Inflation liegt bei 3.5 Prozent.", FREITAG) == []
    assert zeittreue.daten("Gilt ab 1.12", FREITAG) == [date(2026, 12, 1)]
