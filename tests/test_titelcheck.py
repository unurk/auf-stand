"""Titel-Faktencheck (25.11.: „A1 investiert 500 Millionen" — im Text nur 300 Mio. Einsparung)."""
from copilot import main, titelcheck
from copilot.fetch import Article

QUELLE = Article(
    id="1", title="A1 baut um: 500 Millionen Euro für die Zukunft, Stellenabbau in der Gegenwart",
    teaser="", ressort="Wirtschaft", published=None,
    link="https://www.diepresse.com/41486219/a1-baut-um-500-millionen-euro",
)

AUSGABE = """# ☀️ A1 investiert 500 Millionen in die Zukunft
*Mittwoch, 25. November 2026 · Morgen-Ausgabe*

**Heute wichtig:**
1️⃣ A1 investiert 500 Millionen, streicht aber Personal
2️⃣ Lufthansa streicht 1000 Stellen zusätzlich

---

## 1️⃣ 📊 A1 investiert 500 Millionen, streicht aber Personal
**Was ist neu:** A1 Telekom Austria will bis 2030 insgesamt 300 Millionen Euro einsparen, rund ein Drittel davon durch Personalabbau.
**Warum es zählt:** Der Umbau trifft Beschäftigte in Österreich direkt. (Wirtschaft)
[→ Artikel](https://www.diepresse.com/41486219/a1-baut-um-500-millionen-euro)

## 2️⃣ ✈️ Lufthansa streicht 1.000 Stellen zusätzlich
**Was ist neu:** Die AUA-Mutter baut 1000 Stellen zusätzlich zu 4000 bereits beschlossenen ab.
**Warum es zählt:** Der Kostendruck trifft auch die AUA. (Wirtschaft)
[→ Artikel](https://www.diepresse.com/2/lufthansa)

---
"""


def test_a1_fall_zahl_aus_titel_ohne_deckung_im_text():
    out, korrekturen = titelcheck.pruefe_titel(AUSGABE, [QUELLE])
    # Die Quell-Schlagzeile hat dieselbe ungedeckte 500 — taugt nicht als Ersatz
    assert "## 1️⃣ 📊 A1 investiert, streicht aber Personal" in out
    punkte = out[out.index("## 1"):]
    assert "500" not in punkte.split("[→ Artikel]")[0]
    assert any("Punkt 1" in k and "500" in k for k in korrekturen)
    # H1 behauptete die 500 ebenfalls → wird zum geprüften Titel von Punkt 1
    assert out.startswith("# ☀️ A1 investiert, streicht aber Personal\n")
    # Gedeckte Titel bleiben unverändert („1.000" im Titel = „1000" im Text)
    assert "## 2️⃣ ✈️ Lufthansa streicht 1.000 Stellen zusätzlich" in out
    # Link-URL (mit „500" im Slug) bleibt unangetastet
    assert "](https://www.diepresse.com/41486219/a1-baut-um-500-millionen-euro)" in out


def test_heute_wichtig_folgt_dem_geprueften_titel():
    out = main._pruefe_titel(AUSGABE, [QUELLE])
    assert "1️⃣ A1 investiert, streicht aber Personal\n" in out
    assert "1️⃣ A1 investiert 500" not in out


def test_quell_schlagzeile_als_ersatz_wenn_zahlen_gedeckt():
    md = AUSGABE.replace("## 1️⃣ 📊 A1 investiert 500 Millionen, streicht aber Personal",
                         "## 1️⃣ 📊 A1 spart 900 Millionen")
    quelle = Article(id="1", title="A1 will 300 Millionen Euro einsparen", teaser="",
                     ressort="Wirtschaft", published=None, link=QUELLE.link)
    out, _ = titelcheck.pruefe_titel(md, [quelle])
    assert "## 1️⃣ 📊 A1 will 300 Millionen Euro einsparen" in out


def test_namen_und_zahlwoerter_sind_keine_falschmeldung():
    md = """# ☀️ COP31 endet ohne Einigung

## 1️⃣ 🌍 COP31 endet ohne Einigung
**Was ist neu:** Die Weltklimakonferenz in Belém ging ohne Abschluss zu Ende.

## 2️⃣ 📊 Steiermark steuert auf 12-Milliarden-Schuldenberg zu
**Was ist neu:** Bis 2030 könnte der Schuldenstand auf knapp zwölf Milliarden Euro wachsen.
"""
    assert titelcheck.pruefe_titel(md, []) == (md, [])


def test_zahl_am_ende_laesst_kein_verb_ohne_objekt():
    assert titelcheck.streiche_zahlen("SVS-Beiträge: Verpasste Frist kostet 18.632 Euro", set()) \
        == "SVS-Beiträge: Verpasste Frist"
    assert titelcheck.streiche_zahlen("Mayr-Melnhof meldet bis zu 340 Mio. Euro Verlust", set()) \
        == "Mayr-Melnhof meldet Verlust"
    assert titelcheck.streiche_zahlen("Steiermark steuert auf 12-Milliarden-Schuldenberg zu", set()) \
        == "Steiermark steuert auf Milliarden-Schuldenberg zu"


def test_zahlen_normierung():
    assert titelcheck.zahlen("1.000 Jobs, 4,5 Prozent, 2030") == {"1000", "4,5", "2030"}
    assert titelcheck.zahlen("COP31, A1, 5G") == set()
    assert titelcheck.zahlen("knapp zwölf Milliarden") == {"12"}
    assert titelcheck.zahlen("knapp zwölf Milliarden", zahlwoerter=False) == set()
