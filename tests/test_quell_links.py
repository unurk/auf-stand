"""Quell-Link je Punkt (20.–23.11.: bei 8 von 33 Punkten fehlte „Weiterlesen bei der Presse").

Ursache: Das Modell ließ „[→ Artikel](URL)" weg oder setzte den Link auf die
Quellenklammer. Kein Nachbearbeitungs-Schritt entfernt Links — der Link wird
darum nach der Synthese aus dem Material deterministisch nachgetragen.
"""
import re
from datetime import datetime, timezone

from copilot import main, qualitaet, render, telegram, webview
from copilot.fetch import Article


def _a(titel, teaser, link, ressort="Politik"):
    return Article(id=link, title=titel, teaser=teaser, link=link, ressort=ressort,
                   published=datetime.now(timezone.utc))


MATERIAL = [
    _a("Bezirksgerichte: Reform der Gerichtsstruktur auf Eis",
       "Die Zusammenlegung von 16 kleineren Standorten ist vorerst vom Tisch.",
       "https://www.diepresse.com/1/bezirksgerichte", "Recht"),
    _a("COP31: Klimakonferenz endet mit schwachem Kompromiss",
       "Verbindliche Ziele gegen die Erderwärmung fehlen im Abschlussdokument.",
       "https://www.diepresse.com/2/cop31", "Startseite"),
    _a("Klimaschutz: Industrie fordert Planbarkeit",
       "Österreichs Industrie verlangt verlässliche Vorgaben.",
       "https://www.diepresse.com/3/industrie", "Wirtschaft"),
    _a("Lufthansa streicht 1000 Jobs",
       "AUA setzt auf natürliche Abgänge.",
       "https://www.diepresse.com/4/lufthansa", "Wirtschaft"),
]

# Nachgebaut aus 2026-11-23-morgen (Punkt 1) und 2026-11-21-mittag (Punkt 3),
# dazu 2026-11-20-nachmittag (Link auf der Quellenklammer) und ein intakter Punkt.
AUSGABE = """# ☀️ COP31 endet ohne verbindliche Ziele

**Heute wichtig:**
1️⃣ COP31: Klimakonferenz endet mit Minimalkompromiss
2️⃣ Gerichtsreform: Bezirksgerichte bleiben vorerst
3️⃣ Lufthansa streicht 1000 Jobs — AUA verschont
4️⃣ Intakter Punkt

---

## 1️⃣ 🌍 COP31: Klimakonferenz endet mit Minimalkompromiss
**Was ist neu:** Die Klimakonferenz endet ohne verbindliche Ziele gegen die Erderwärmung.
**Warum es zählt:** Für Österreichs Industrie bedeutet das weniger Planbarkeit.
Beschlossen

## 2️⃣ ⚖️ Gerichtsreform: Bezirksgerichte bleiben vorerst
**Was ist neu:** Die Zusammenlegung von 16 kleineren Standorten liegt auf Eis.
**Warum es zählt:** Für Klagende bleibt es beim Status quo. (Recht)

## 3️⃣ ✈️ Lufthansa streicht 1000 Jobs — AUA verschont
**Was ist neu:** Die AUA-Mutter baut in Deutschland Stellen ab.
**Warum es zählt:** Für AUA-Beschäftigte vorerst Jobsicherheit.
[Wirtschaft · Bericht: fed/APA](https://www.diepresse.com/4/lufthansa)

## 4️⃣ 🏛 Intakter Punkt
**Was ist neu:** Etwas.
**Warum es zählt:** Folgen. (Politik)
[→ Artikel](https://www.diepresse.com/9/intakt)

---

## 🔍 Geprüft, nicht aufgenommen
- Etwas anderes

---
✓ Du bist informiert
"""


def _punkte(md):
    return [t for t in re.split(r"(?m)^(?=## |---)", md) if re.match(r"## \d", t)]


def test_jeder_punkt_hat_danach_einen_quell_link():
    out, ergaenzt, umgebaut = qualitaet.sichere_quell_links(AUSGABE, MATERIAL)
    assert (ergaenzt, umgebaut) == (2, 1)
    links = [re.findall(r"\[→ Artikel\]\(([^)]+)\)", p) for p in _punkte(out)]
    assert links == [
        ["https://www.diepresse.com/2/cop31"],          # passendste von zwei Klima-Quellen
        ["https://www.diepresse.com/1/bezirksgerichte"],
        ["https://www.diepresse.com/4/lufthansa"],
        ["https://www.diepresse.com/9/intakt"],         # unverändert
    ]
    assert "(Wirtschaft · Bericht: fed/APA) [→ Artikel](https://www.diepresse.com/4/lufthansa)" in out
    # Link steht am Ende des Punkts, nicht hinter dem Trenner
    assert "Beschlossen\n[→ Artikel](https://www.diepresse.com/2/cop31)\n\n## 2" in out
    # Nicht-Punkte (Geprüft …) bekommen keinen Link
    assert "Etwas anderes\n\n---" in out


def test_ohne_passenden_artikel_kein_link():
    fremd = [_a("Wetter: Schnee im Westen", "Kalt.", "https://www.diepresse.com/7/wetter")]
    out, ergaenzt, _ = qualitaet.sichere_quell_links(AUSGABE, fremd)
    assert ergaenzt == 0
    assert "diepresse.com/7/wetter" not in out


def test_idempotent_und_intakte_ausgabe_unveraendert():
    einmal, _, _ = qualitaet.sichere_quell_links(AUSGABE, MATERIAL)
    assert qualitaet.sichere_quell_links(einmal, MATERIAL) == (einmal, 0, 0)


def test_englische_edition_nutzt_article():
    out, _, _ = qualitaet.sichere_quell_links(AUSGABE, MATERIAL, "en")
    assert "[→ Article](https://www.diepresse.com/2/cop31)" in out


def test_web_zeigt_weiterlesen_bei_jedem_punkt(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", tmp_path)
    out = main._sichere_quell_links(AUSGABE, MATERIAL, "de")
    _, html_path = render.write_output(out, "morgen")
    html = html_path.read_text(encoding="utf-8")
    body = webview._enhance_content(html[html.index("<h1>"):html.index("</body>")],
                                    "2026-11-23", "morgen")
    teile = [t for t in re.split(r"(?=<h2>)", body) if t.startswith("<h2>")]
    assert len(teile) == 4
    assert all('class="source-link"' in t for t in teile)


def test_telegram_zeigt_link_bei_jedem_punkt():
    out = main._sichere_quell_links(AUSGABE, MATERIAL, "de")
    tg = telegram._to_telegram_md(out)
    for url in ("2/cop31", "1/bezirksgerichte", "4/lufthansa", "9/intakt"):
        assert f"[→ Artikel](https://www.diepresse.com/{url})" in tg
