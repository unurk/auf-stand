"""Regression 26.11.: Schlagzeile „USA drosseln EU-Zölle" und ungedeckte „100 Millionen" (Wien)."""
import re

from copilot import budget, main, qualitaet, titelcheck

PUNKTE = """
## 1️⃣ 🌍 USA planen neue Zölle gegen EU und 13 Handelspartner
**Was ist neu:** Laut dem US-Handelsbeauftragten soll eine vereinbarte Zoll-Obergrenze von 15 Prozent für die EU eingehalten werden. Die neue Zollrunde richtet sich gegen die EU und 13 weitere Handelspartner.
**Warum es zählt:** Für die österreichische Exportwirtschaft bedeutet das eine neuerliche Belastung. (Wirtschaft)
[→ Artikel](https://www.diepresse.com/41491374/usa-planen-neue-zoelle-gegen-eu-und-13-weitere-handelspartner)

## 2️⃣ 📊 Geplant: A1 investiert, streicht aber Personal
**Was ist neu:** A1 Telekom Austria will bis 2030 insgesamt 300 Millionen Euro einsparen, davon rund ein Drittel durch Personalabbau.
**Warum es zählt:** Der Abbau trifft Beschäftigte in Österreich direkt. (Wirtschaft)
[→ Artikel](https://www.diepresse.com/41486219/a1-baut-um-500-millionen-euro)

## 3️⃣ ⚖️ OGH: Arbeitgeber müssen Internetkosten im Homeoffice zahlen
**Was ist neu:** Der OGH entschied, dass die „digitalen Arbeitsmittel“ auch die Internetverbindung umfassen. Das betrifft viele Dienstverträge. Arbeitgeber müssen nachzahlen.
**Warum es zählt:** Das Urteil verpflichtet Unternehmen zu einer neuen Ausgabe, die bisher strittig war. Viele Firmen müssen ihre Regelungen anpassen. (Recht)
[→ Artikel](https://www.diepresse.com/41489486/arbeitgeber-internet-homeoffice)

## 4️⃣ 🏛 Wien muss 100 Millionen Euro bei Mindestsicherung sparen
**Was ist neu:** Die Kosten für die Mindestsicherung sind in Wien auf 1,1 Milliarden Euro explodiert. Die Stadt muss deshalb im kommenden Jahr 100 Millionen Euro einsparen. Betroffen sind vor allem Zusatzleistungen.
**Warum es zählt:** Die Einsparungen betreffen Unterstützungsleistungen und bringen die Stadt finanziell in Bedrängnis. Die Opposition kündigt Widerstand an. (Wien)
[→ Artikel](https://www.diepresse.com/41485850/wien-gibt-1-1-milliarden-fuer-die-mindestsicherung-aus)
"""


def _ausgabe(h1: str) -> str:
    return (
        f"# ☀️ {h1}\n*Donnerstag, 26. November 2026 · Morgen-Ausgabe*\n\n**Heute wichtig:**\n"
        "1️⃣ USA planen neue Zölle gegen EU und 13 Handelspartner\n"
        "2️⃣ Geplant: A1 investiert, streicht aber Personal\n"
        "3️⃣ OGH: Arbeitgeber müssen Internetkosten im Homeoffice zahlen\n"
        "4️⃣ Wien muss 100 Millionen Euro bei Mindestsicherung sparen\n\n---\n"
        + PUNKTE
        + "\n## 🔍 Geprüft, nicht aufgenommen\n"
        + "\n".join(f"- Meldung {i} — knapp unter der Schwelle, ohne Folgen für dich" for i in range(4))
        + "\n\n---\n\n✓ Du bist informiert — Lesezeit ca. 90 Sekunden.\n"
    )


# ── Schlagzeile „drosseln" vs. Punkt „planen neue Zölle" ────────────────────

def test_schlagzeile_mit_falscher_richtung_faellt_auf_punkt_1_zurueck():
    md = _ausgabe("USA drosseln EU-Zölle auf 15 Prozent, A1 streicht Stellen")
    out, korrekturen = titelcheck.pruefe_titel(md, [])
    assert out.startswith("# ☀️ USA planen neue Zölle gegen EU und 13 Handelspartner\n")
    grund = next(k for k in korrekturen if k.startswith("H1")).split(" — ")[0]
    assert "drosseln" in grund
    # Die 15 Prozent stehen im Text — die Zahlen-Prüfung allein hätte durchgelassen
    assert "Zahl" not in grund


def test_schlagzeile_rueckfall_auch_ueber_die_pipeline():
    out = main._pruefe_titel(_ausgabe("USA drosseln EU-Zölle auf 15 Prozent, A1 streicht Stellen"), [])
    assert out.splitlines()[0] == "# ☀️ USA planen neue Zölle gegen EU und 13 Handelspartner"
    assert "drosseln" not in out


def test_gedeckte_schlagzeile_bleibt():
    for h1 in ("USA planen neue Zölle, A1 streicht Personal",
               "Neue US-Zölle gegen EU und 13 Handelspartner",
               "Wien muss bei der Mindestsicherung 100 Millionen sparen"):
        md = _ausgabe(h1)
        assert titelcheck.pruefe_titel(md, []) == (md, []), h1


def test_ungedeckte_zahl_in_schlagzeile_faellt_zurueck():
    out, _ = titelcheck.pruefe_titel(_ausgabe("USA planen neue Zölle von 25 Prozent"), [])
    assert out.startswith("# ☀️ USA planen neue Zölle gegen EU und 13 Handelspartner\n")


# ── Wien: 100 Millionen dürfen nicht der Kürzung zum Opfer fallen ────────────

def _punkt(md, nummer):
    return next(t for t in re.split(r"(?m)^(?=## |---)", md) if t.startswith(f"## {nummer}"))


def test_kuerzung_behaelt_satz_der_die_titel_zahl_deckt():
    md = _ausgabe("USA planen neue Zölle gegen EU und 13 Handelspartner")
    assert qualitaet.lesezeit_sekunden(md, 3.2) > 75
    out, schritte = budget.kuerze_auf_budget(md, 75, 3.2)
    assert "letzten Punkt gestrichen" not in schritte
    assert "„Was ist neu“ ab Punkt 2 auf 1 Satz" in schritte
    wien = _punkt(out, 4)
    # Erster Satz + der Satz mit der Titel-Zahl; der dritte Satz ist weg
    assert "1,1 Milliarden" in wien and "100 Millionen Euro einsparen" in wien
    assert "Zusatzleistungen" not in wien
    # Andere Punkte werden normal auf einen Satz gekürzt
    assert "Arbeitgeber müssen nachzahlen" not in _punkt(out, 3)
    # Danach meldet der Titel-Check nichts: der Wien-Titel ist gedeckt
    assert titelcheck.pruefe_titel(out, []) == (out, [])


def test_ohne_schutz_waere_der_wien_titel_ungedeckt():
    """Belegt den Mechanismus vom 26.11.: nur der erste Satz → „100" fehlt im Text."""
    zeile = next(l for l in _punkt(_ausgabe("x"), 4).splitlines() if l.startswith("**Was ist neu:**"))
    nur_erster = budget._kuerze_zeile(zeile, "**Was ist neu:**", 1)
    assert "100" not in nur_erster
    mit_schutz = budget._kuerze_zeile(zeile, "**Was ist neu:**", 1, {"100"})
    assert "100 Millionen" in mit_schutz
