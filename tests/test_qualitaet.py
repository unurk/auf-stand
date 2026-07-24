"""Qualitäts-Gate: leere Themen-Deltas raus, Abschnitt gedeckelt, Budget gemessen."""
from copilot import qualitaet


LAGEBILD = """# Lagebild

## 1️⃣ Ein Punkt
Text.

## Deine Themen
- **EZB:** Seit deinem letzten Stand wurde der Leitzins gesenkt.
- **Börse:** Seit deinem letzten Stand hat sich nichts Wesentliches getan.
- **Miet:** Seit deinem letzten Stand bleibt es bei der bisherigen Einschätzung.
- **Zoll:** Seit deinem letzten Stand gelten die Zölle fix.
- **EU:** Seit deinem letzten Stand ist das Sanktionspaket beschlossen.
- **Energie:** Seit deinem letzten Stand ist Diesel über 2 Euro.

---
✅ Du bist informiert
"""


def test_leere_deltas_werden_erkannt():
    assert qualitaet.ist_leeres_delta("- Börse: hat sich nichts Wesentliches getan.")
    assert qualitaet.ist_leeres_delta("- Miet: bleibt es bei der Einschätzung")
    assert qualitaet.ist_leeres_delta("- Fed: no material change so far")
    assert not qualitaet.ist_leeres_delta("- EZB: Der Leitzins wurde gesenkt.")


def test_trim_entfernt_leere_und_deckelt_auf_drei():
    out, report = qualitaet.trim_tracker_section(LAGEBILD)
    zeilen = [l for l in out.splitlines() if l.startswith("- ")]
    assert len(zeilen) == 3
    assert report["entfernt"] == 3  # 2 leere + 1 über dem Deckel
    assert "nichts Wesentliches" not in out
    assert "Leitzins gesenkt" in out  # stärkste Änderung bleibt vorn
    # Alles außerhalb des Abschnitts bleibt unangetastet
    assert "## 1️⃣ Ein Punkt" in out
    assert "Du bist informiert" in out


def test_trim_entfernt_ueberschrift_wenn_nichts_bleibt():
    md = (
        "# L\n\n## Deine Themen\n"
        "- **Börse:** Seit deinem letzten Stand hat sich nichts getan.\n\n"
        "---\n✅ Du bist informiert\n"
    )
    out, report = qualitaet.trim_tracker_section(md)
    assert "Deine Themen" not in out
    assert report["behalten"] == 0
    assert "Du bist informiert" in out


def test_trim_ohne_abschnitt_ist_no_op():
    md = "# L\n\n## 1️⃣ Punkt\nText.\n"
    out, report = qualitaet.trim_tracker_section(md)
    assert out == md
    assert report["entfernt"] == 0


def test_lange_zeile_wird_gekappt():
    lang = "- **EZB:** " + " ".join(f"wort{i}" for i in range(60))
    md = f"# L\n\n## Deine Themen\n{lang}\n\n---\n"
    out, report = qualitaet.trim_tracker_section(md)
    assert report["gekappt"] == 1
    zeile = next(l for l in out.splitlines() if l.startswith("- "))
    assert len(zeile.split()) <= qualitaet.MAX_TRACKER_WOERTER + 2


def test_budget_warnt_nur_bei_ueberlaenge():
    kurz = " ".join(["wort"] * 200)   # ~62 s bei 3.2 W/s
    lang = " ".join(["wort"] * 600)   # ~190 s
    assert qualitaet.pruefe_budget(kurz, 90) == ""
    assert "Budget gerissen" in qualitaet.pruefe_budget(lang, 90)


def test_budget_hinweis_erst_ab_drei_werten():
    assert qualitaet.budget_hinweis([150, 160], 90) == ""
    assert qualitaet.budget_hinweis([60, 75, 60], 90) == ""
    hinweis = qualitaet.budget_hinweis([150, 165, 180], 90)
    assert "165" in hinweis and "kürzer" in hinweis
