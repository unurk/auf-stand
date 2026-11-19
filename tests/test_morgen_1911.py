"""Qualitätsfixes aus der Morgen-Ausgabe vom 19.11.2026.

1) H1 „Bereit?" — Meta-Floskel statt Schlagzeile.
2) Punkt „Medienförderung" ohne „Was ist neu:"/„Warum es zählt:".
3) „Deine Themen" wiederholte Punkte (Airbnb/Kurzzeitvermietung, Anthropic/Nvidia).
4) Kopfzeile „Die Presse · Copilot" — geprüft: gewollter Produktname.
"""
from copilot import i18n, main, qualitaet, render, state, synthesize, webview

AUSGABE = """# ☀️ Dein Lagebild — Donnerstag, 19. November 2026 · Morgen-Ausgabe

**Heute wichtig:**
1️⃣ Alle Eisenbahner bekommen 38,5-Stunden-Woche
2️⃣ Wien verschärft Regeln für Kurzzeitvermietung
3️⃣ Anthropic-Börsengang beschert Gründern Milliarden
4️⃣ Nationalrat beschließt Ausbau der Medienförderung

---

## 1️⃣ 📊 Alle Eisenbahner bekommen 38,5-Stunden-Woche
**Was ist neu:** Die Wochenarbeitszeit für alle Eisenbahner sinkt von 40 auf 38,5 Stunden.
**Warum es zählt:** Den Beschäftigten bei ÖBB entsteht mehr Freizeit. (Wirtschaft) [→ Artikel](https://www.diepresse.com/1)

## 2️⃣ 🏠 Wien verschärft Regeln für Kurzzeitvermietung
**Was ist neu:** Der Wiener Landesgesetzgeber begrenzt das Home-Sharing auf eine Wohnung pro Anbieter und führt ein neues Register ein.
**Warum es zählt:** Wer in Wien Wohnungen über Plattformen vermietet, muss sich auf strengere Regeln einstellen. (Wohnen) [→ Artikel](https://www.diepresse.com/2)

## 3️⃣ 📊 Anthropic-Börsengang beschert Gründern Milliarden
**Was ist neu:** Das KI-Unternehmen Anthropic vollzieht heute den Börsengang. Der Schritt folgt auf solide Quartalszahlen von Konkurrent Nvidia.
**Warum es zählt:** Investoren setzen weiter massiv auf KI-Technologie. (Wirtschaft) [→ Artikel](https://www.diepresse.com/3)

## 4️⃣ 🏛 Nationalrat beschließt Ausbau der Medienförderung
Die Zustellförderung für Tageszeitungen wird auf Beschluss des Nationalrats ausgeweitet und sichert kleineren Medien dringend nötige Einnahmen. (Politik) [→ Artikel](https://www.diepresse.com/4)
**Reifegrad:** Beschlossen

## Deine Themen
- **US-Börsen:** Nvidia liefert nach Abgang von Jensen Huang bessere Quartalszahlen als erwartet und gibt dem von Anthropic angetriebenen KI-Sektor Rückenwind.
- **Mietrecht und Wohnkosten:** Wien zieht die Schraube bei Airbnb mit Beschränkung auf eine Wohnung und neuem Register weiter an — ein direkter Eingriff in lokale Nutzungsrechte.

---
✅ *Du bist informiert — Lesezeit ca. 90 Sekunden.*
"""


# ── 1) Überschrift ───────────────────────────────────────────────────────────

def test_meta_ueberschriften_werden_erkannt():
    for meta in ("Bereit?", "Guten Morgen.", "Guten Morgen. Los geht's.", "Los geht's",
                 "Dein Lagebild", "Dein Lagebild — Donnerstag, 19. November · Morgen-Ausgabe",
                 "Schön, dass du da bist.", "Your Briefing — Thursday, November 19"):
        assert qualitaet.ist_meta_ueberschrift(meta), meta
    for echt in ("Alle Eisenbahner bekommen 38,5-Stunden-Woche", "Ruhige Lage",
                 "Halbzeit bei den Koalitionsverhandlungen", "Update zur Pensionsreform"):
        assert not qualitaet.ist_meta_ueberschrift(echt), echt


def test_meta_h1_wird_durch_aufmacher_ersetzt():
    md, geaendert = qualitaet.korrigiere_h1(AUSGABE.replace(
        "# ☀️ Dein Lagebild — Donnerstag, 19. November 2026 · Morgen-Ausgabe", "# ☀️ Bereit?"))
    assert geaendert
    assert md.splitlines()[0] == "# ☀️ Alle Eisenbahner bekommen 38,5-Stunden-Woche"


def test_echte_h1_bleibt():
    md = AUSGABE.replace("# ☀️ Dein Lagebild — Donnerstag, 19. November 2026 · Morgen-Ausgabe",
                         "# ☀️ Eisenbahn: kürzere Woche, gleiches Geld")
    assert qualitaet.korrigiere_h1(md) == (md, False)


def test_ohne_punkte_wird_h1_ruhige_lage():
    md, _ = qualitaet.korrigiere_h1("# 🌙 Guten Abend.\n\nNichts Neues.\n")
    assert md.startswith("# 🌙 Ruhige Lage")


def test_webseite_zeigt_schlagzeile_statt_begruessung():
    """Auch archivierte Seiten mit „Bereit?" bekommen beim Site-Build die Schlagzeile."""
    html = (
        '<header class="lagebild-header"><p class="kicker">x</p><h1>Bereit?</h1>'
        '<p class="byline">y</p></header>'
        "<h2>Alle Eisenbahner bekommen 38,5-Stunden-Woche</h2><p>Text</p><hr>"
    )
    body = webview._enhance_content(html, "2026-11-19", "morgen", "de")
    assert "<h1>Alle Eisenbahner bekommen 38,5-Stunden-Woche</h1>" in body
    assert "Bereit?" not in body


def test_frische_ausgabe_web_h1_und_keine_datumszeile(tmp_path, monkeypatch):
    monkeypatch.setattr(render, "OUT_DIR", tmp_path)
    md = "# ☀️ Eisenbahn: kürzere Woche\n*Donnerstag, 19. November 2026 · Morgen-Ausgabe*\n\n" \
         + AUSGABE.split("\n", 1)[1]
    _, html_path = render.write_output(md, "morgen", "de")
    body = webview._extract_body(html_path.read_text(encoding="utf-8"), "2026-11-19", "morgen", "de")
    assert "<h1>Eisenbahn: kürzere Woche</h1>" in body
    assert "<em>Donnerstag, 19. November 2026" not in body  # Datum steht im Kicker


# ── 2) Struktur ──────────────────────────────────────────────────────────────

def test_fehlende_struktur_wird_erkannt():
    assert qualitaet.fehlende_struktur(AUSGABE) == [4]


def test_fliesstext_punkt_wird_gegliedert():
    md, n = qualitaet.repariere_struktur(AUSGABE)
    assert n == 1 and qualitaet.fehlende_struktur(md) == []
    punkt4 = md.split("## 4️⃣")[1].split("## Deine")[0]
    assert ("**Was ist neu:** Die Zustellförderung für Tageszeitungen wird auf Beschluss "
            "des Nationalrats ausgeweitet.") in punkt4
    assert ("**Warum es zählt:** Das sichert kleineren Medien dringend nötige Einnahmen. "
            "(Politik) [→ Artikel](https://www.diepresse.com/4)") in punkt4
    assert "**Reifegrad:** Beschlossen" in punkt4
    # andere Punkte unverändert
    assert md.split("## 4️⃣")[0] == AUSGABE.split("## 4️⃣")[0]


def test_mehrere_saetze_erster_ist_neu_rest_warum():
    md = "## 1️⃣ 📊 X\nDer Zins sinkt. Kredite werden billiger. Sparer verlieren.\n"
    out, n = qualitaet.repariere_struktur(md)
    assert n == 1
    assert "**Was ist neu:** Der Zins sinkt.\n**Warum es zählt:** Kredite werden billiger. Sparer verlieren." in out


def test_pipeline_versucht_erst_neuversuch(monkeypatch):
    aufrufe = []

    def fake(lagebild, punkte, config, lang="de"):
        aufrufe.append(punkte)
        return lagebild  # Modell hilft nicht → deterministische Reparatur greift

    monkeypatch.setattr(synthesize, "repariere_struktur", fake)
    out = main._bereinige_modell_output(AUSGABE, "de", config={"provider": "anthropic"})
    assert aufrufe == [[4]]
    assert qualitaet.fehlende_struktur(out) == []


def test_modell_reparatur_wird_nur_bei_verbesserung_uebernommen(monkeypatch):
    monkeypatch.setattr(synthesize, "_provider_configured", lambda c: True)
    monkeypatch.setattr(synthesize, "_complete", lambda *a, **k: AUSGABE)  # unverändert
    assert synthesize.repariere_struktur(AUSGABE, [4], {}) == AUSGABE
    gut = AUSGABE.replace(
        "Die Zustellförderung für Tageszeitungen wird auf Beschluss des Nationalrats ausgeweitet und sichert",
        "**Was ist neu:** Der Nationalrat weitet die Zustellförderung aus.\n**Warum es zählt:** Das sichert",
    )
    monkeypatch.setattr(synthesize, "_complete", lambda *a, **k: gut)
    assert synthesize.repariere_struktur(AUSGABE, [4], {}) == gut


# ── 3) Keine Doppelungen in „Deine Themen" ───────────────────────────────────

def test_doppelte_themen_zeilen_fallen_und_abschnitt_entfaellt():
    md, n = qualitaet.entferne_themen_doppelungen(AUSGABE)
    assert n == 2
    assert "## Deine Themen" not in md
    assert "Airbnb" not in md and "Jensen Huang" not in md
    assert "## 4️⃣" in md and md.rstrip().endswith("✅ *Du bist informiert — Lesezeit ca. 90 Sekunden.*")


def test_eigenstaendige_themen_zeile_bleibt():
    md = AUSGABE.replace(
        "- **US-Börsen:** Nvidia liefert",
        "- **EZB:** Seit deinem letzten Stand: Leitzins um 25 Basispunkte gesenkt, Sparzinsen sinken.\n"
        "- **US-Börsen:** Nvidia liefert",
    )
    out, n = qualitaet.entferne_themen_doppelungen(md)
    assert n == 2
    assert "## Deine Themen\n- **EZB:** Seit deinem letzten Stand: Leitzins" in out


def test_dossier_behaelt_entfernte_zeilen():
    """Die Ausgabe zeigt die Doppelung nicht — der Tracker-Verlauf bekommt sie trotzdem."""
    s: dict = {}
    topics = [{"name": "Mietrecht und Wohnkosten", "schlagwort": "Mietrecht"}]
    state.update_dossier(s, AUSGABE, topics, "2026-11-19")  # main übergibt die Fassung vor dem Gate
    assert "Airbnb" in s["dossier"]["Mietrecht und Wohnkosten"][0]["summary"]


# ── 4) Kopfzeile „Die Presse · Copilot" ──────────────────────────────────────

def test_kopfzeile_copilot_ist_gewollter_produktname():
    """„Copilot" ist der Produktname (PWA-Manifest, Push, Podcast, Mail-Brand), kein
    Überbleibsel. Der Test hält Kopfzeile und Brand-String konsistent."""
    assert '<div class="wordmark-text">Die Presse</div>' in webview._PAGE_TEMPLATE
    assert '<div class="copilot-pill">Copilot</div>' in webview._PAGE_TEMPLATE
    assert i18n.t("de", "brand") == "Die Presse · Copilot"
    assert i18n.t("de", "podcast_title").startswith("Die Presse · Copilot")
