"""Lesezeit-Budget 90 s durchsetzen (24.11.: 135 s, 25.11.: 120 s)."""
import re

from copilot import budget, qualitaet

WPS = 3.2
SATZ = "Die Regierung legt dazu einen detaillierten Plan mit mehreren Etappen vor. "


def _punkt(n, saetze_neu=4, saetze_warum=2, kommt=True):
    zeilen = [
        f"## {n}️⃣ 📊 Punkt {n} mit klarer Überschrift",
        "**Was ist neu:** " + SATZ * saetze_neu,
        "**Warum es zählt:** " + "Für dich wird das spürbar teurer, etwa 340 Mio. Euro. " * saetze_warum
        + f"(Wirtschaft · Bericht: Autor {n})",
    ]
    if kommt:
        zeilen.append("**Was kommt:** Im Jänner entscheidet der Nationalrat darüber.")
    zeilen.append(f"[→ Artikel](https://www.diepresse.com/4148{n}/ein-sehr-langer-slug-mit-vielen-woertern)")
    return "\n".join(zeilen)


def _ausgabe(punkte=5, **kw):
    heute = "\n".join(f"{n}️⃣ Punkt {n} mit klarer Überschrift" for n in range(1, punkte + 1))
    return (
        "# ☀️ Punkt 1 mit klarer Überschrift\n*Mittwoch, 25. November 2026 · Morgen-Ausgabe*\n\n"
        f"**Heute wichtig:**\n{heute}\n\n---\n\n"
        + "\n\n".join(_punkt(n, **kw) for n in range(1, punkte + 1))
        + "\n\n## 🔍 Geprüft, nicht aufgenommen\n"
        + "\n".join(f"- Meldung {i} — knapp unter der Schwelle, ohne Folgen für dich" for i in range(4))
        + "\n\n---\n\n✓ Du bist informiert — Lesezeit ca. 90 Sekunden.\n"
    )


def _links(md):
    return re.findall(r"\[→ Artikel\]\(([^)]+)\)", md)


def test_lange_ausgabe_wird_auf_90_sekunden_gekuerzt():
    md = _ausgabe()
    assert qualitaet.lesezeit_sekunden(md, WPS) > 90
    out, schritte = budget.kuerze_auf_budget(md, 90, WPS)
    assert qualitaet.lesezeit_sekunden(out, WPS) <= 90
    assert schritte
    # Keine Quell-Links verloren, alle Punkte (Top-Meldungen) noch da
    assert _links(out) == _links(md)
    assert len(re.findall(r"(?m)^## \d", out)) == 5
    # Quellenklammer bleibt am gekürzten „Warum es zählt" hängen
    assert out.count("(Wirtschaft · Bericht: Autor") == 5
    # Aufmacher-Titel und H1 unverändert
    assert "## 1️⃣ 📊 Punkt 1 mit klarer Überschrift" in out
    assert out.startswith("# ☀️ Punkt 1 mit klarer Überschrift")


def test_kurze_ausgabe_bleibt_unveraendert():
    md = _ausgabe(punkte=2, saetze_neu=1, saetze_warum=1, kommt=False)
    assert qualitaet.lesezeit_sekunden(md, WPS) <= 90
    assert budget.kuerze_auf_budget(md, 90, WPS) == (md, [])


def test_letzter_ausweg_streicht_hintere_punkte_nie_unter_drei():
    md = _ausgabe(punkte=5).replace(SATZ, SATZ * 3)  # extrem lang
    out, schritte = budget.kuerze_auf_budget(md, 60, WPS)
    punkte = re.findall(r"(?m)^## (\d)", out)
    assert len(punkte) >= 3 and punkte[0] == "1"
    assert "letzten Punkt gestrichen" in schritte
    assert qualitaet.lesezeit_sekunden(out, WPS) <= 60
    # „Heute wichtig" spiegelt die verbliebenen Punkte, jeder hat seinen Link
    heute = re.findall(r"(?m)^(\d)️⃣ ", out)
    assert heute == punkte
    assert len(_links(out)) == len(punkte)


def test_satzgrenze_robust_gegen_abkuerzungen_und_daten():
    t = "Der Verlust beträgt 340 Mio. Euro. Am 20. November folgt mehr. Dritter Satz."
    assert budget.erster_satz(t) == "Der Verlust beträgt 340 Mio. Euro."
    assert budget.erster_satz(t, 2) == "Der Verlust beträgt 340 Mio. Euro. Am 20. November folgt mehr."


def test_lesezeit_zaehlt_keine_url_woerter():
    ohne = "Ein kurzer Satz mit sieben Wörtern hier."
    mit = ohne + " [→ Artikel](https://www.diepresse.com/1/ein-sehr-langer-slug-mit-vielen-woertern-darin)"
    assert len(re.findall(r"\w+", mit)) - len(re.findall(r"\w+", ohne)) > 10
    w = lambda t: len(re.findall(r"\w+", re.sub(r"\]\([^)]*\)", "]", t)))  # noqa: E731
    assert w(mit) - w(ohne) == 1  # nur „Artikel"
    assert qualitaet.lesezeit_sekunden(" ".join([mit] * 40), WPS) == qualitaet.lesezeit_sekunden(
        " ".join([ohne + " → Artikel"] * 40), WPS)
