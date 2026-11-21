"""Leserprofil aus Feedback (Backlog 5): Votes → Gewichte mit Abklingen → Auswahl."""
from datetime import date, datetime, timezone

from copilot import leserprofil, main, render, state, synthesize
from copilot.fetch import Article, FetchResult

HEUTE = date(2026, 11, 21)
TOPICS = [
    {"name": "Mietrecht und Wohnkosten in Österreich", "schlagwort": "Miet"},
    {"name": "EU-Politik und Österreich", "schlagwort": "EU"},
    {"name": "Ukraine-Krieg und Sicherheitspolitik", "schlagwort": "Ukraine"},
]
KONFIG_ZAEHLER = {"engagement": {"zaehler_url": "https://zaehler.example", "namespace": "auf-stand-test"}}

LAGEBILD = """# ☀️ Mieten steigen weiter

**Heute wichtig:**
1️⃣ Mietpreisbremse: Regierung legt Entwurf vor
2️⃣ Ukraine: Neue Gespräche in Genf

---

## 1️⃣ 🏠 Mietpreisbremse: Regierung legt Entwurf vor
**Was ist neu:** Die Mieten sollen 2027 höchstens um zwei Prozent steigen.
**Warum es zählt:** Wer zur Miete wohnt, zahlt weniger. (Immobilien · Bericht: Anna Muster)
[→ Artikel](https://www.diepresse.com/1/miete)

## 2️⃣ 🌍 Ukraine: Neue Gespräche in Genf
**Was ist neu:** Beide Seiten verhandeln wieder.
**Warum es zählt:** Ein Waffenstillstand senkt Energiepreise. (Ausland)
[→ Artikel](https://www.diepresse.com/2/ukraine)

---
"""


def _artikel(titel, ressort, teaser="", link=""):
    return Article(id=titel, title=titel, teaser=teaser, link=link, ressort=ressort,
                   published=datetime.now(timezone.utc))


def _vote(datum, idx, rating, merkmale, quelle="telegram", chat="1"):
    return {"date": datum, "edition": "morgen", "article_idx": idx, "heading": "",
            "rating": rating, "chat_id": chat, "quelle": quelle, "merkmale": merkmale}


# ── Merkmale je Punkt ────────────────────────────────────────────────────────

def test_merkmale_thema_ressort_stichwort():
    keys = leserprofil.merkmale("Mietpreisbremse kommt 2027", "", ["Immobilien"], TOPICS)
    assert "thema:Mietrecht und Wohnkosten in Österreich" in keys
    assert "ressort:Immobilien" in keys
    assert "wort:mietpre" in keys
    # „EU" trifft nur am Wortanfang — nicht in „neue"/„teuer"
    assert not any(k.startswith("thema:EU") for k in
                   leserprofil.merkmale("Neue Steuer wird teuer", "", [], TOPICS))


def test_startseite_ist_kein_ressort_merkmal():
    assert leserprofil.merkmale("Etwas", "", ["Startseite"], []) == ["wort:etwas"]


def test_punkt_merkmale_aus_lagebild():
    artikel = [_artikel("x", "Politik", link="https://www.diepresse.com/2/ukraine")]
    je_punkt = leserprofil.punkt_merkmale_aus_lagebild(LAGEBILD, artikel, TOPICS)
    assert len(je_punkt) == 2
    assert "ressort:Immobilien" in je_punkt[0]           # aus der Quellenklammer
    assert "thema:Mietrecht und Wohnkosten in Österreich" in je_punkt[0]
    assert {"ressort:Ausland", "ressort:Politik"} <= set(je_punkt[1])  # Klammer + Link
    assert "thema:Ukraine-Krieg und Sicherheitspolitik" in je_punkt[1]


def test_telegram_vote_traegt_merkmale_des_punkts():
    s = {"edition_points": {"2026-11-21|morgen": ["Miete", "Ukraine"]}}
    leserprofil.merke_punkt_merkmale(s, "2026-11-21", "morgen",
                                     [["ressort:Immobilien"], ["ressort:Ausland"]])
    state.record_article_feedback(s, "2026-11-21", "morgen", 1, "down", "42")
    e = s["article_feedback"][-1]
    assert e["merkmale"] == ["ressort:Ausland"] and e["quelle"] == "telegram"


# ── Profil: Gewichte mit Abklingen ───────────────────────────────────────────

def test_ohne_feedback_leeres_profil():
    p = leserprofil.berechne_profil({}, HEUTE)
    assert p["gewichte"] == {} and p["votes"] == 0
    assert leserprofil.prompt_block(p) == ""


def test_alte_votes_zaehlen_weniger():
    s = {"article_feedback": [
        _vote("2026-11-21", 0, "up", ["ressort:Recht"]),
        _vote("2026-11-07", 0, "up", ["ressort:Wirtschaft"]),  # 14 Tage = halbes Gewicht
    ]}
    g = leserprofil.berechne_profil(s, HEUTE)["gewichte"]
    assert g["ressort:Recht"] == 1.0
    assert g["ressort:Wirtschaft"] == 0.5


def test_telegram_umentscheiden_zaehlt_nur_letzten_tap():
    s = {"article_feedback": [
        _vote("2026-11-21", 0, "up", ["ressort:Recht"]),
        _vote("2026-11-21", 0, "down", ["ressort:Recht"]),
    ]}
    assert leserprofil.berechne_profil(s, HEUTE)["gewichte"]["ressort:Recht"] == -1.0


def test_stichwoerter_zaehlen_halb():
    s = {"article_feedback": [_vote("2026-11-21", 0, "down", ["wort:tesla"])]}
    assert leserprofil.berechne_profil(s, HEUTE)["gewichte"]["wort:tesla"] == -0.5


# ── Auswahl ──────────────────────────────────────────────────────────────────

def _material():
    return [
        _artikel("Tesla-Klage in Wien", "Wirtschaft"),
        _artikel("Bundesliga: Rapid verliert", "Sport"),
        _artikel("Mietpreisbremse beschlossen", "Immobilien"),
        _artikel("Regierungskrise: Kanzler tritt zurück", "Startseite"),
        _artikel("Neue Börsenregeln", "Wirtschaft"),
        _artikel("Rapid-Trainer entlassen", "Sport"),
        _artikel("Gericht kippt Gesetz", "Recht"),
        _artikel("Wetter wird kalt", "Panorama"),
    ]


def test_ohne_profil_bleibt_material_unveraendert():
    material = _material()
    geordnet, weg = leserprofil.ordne_material(material, {"gewichte": {}}, TOPICS)
    assert geordnet == material and weg == []


def test_relevant_rueckt_nach_vorne_weniger_faellt_weg():
    profil = {"gewichte": {"ressort:Immobilien": 2.0, "ressort:Sport": -3.0}}
    geordnet, weg = leserprofil.ordne_material(_material(), profil, TOPICS)
    assert geordnet[0].title == "Mietpreisbremse beschlossen"
    # Höchstens ein Viertel fällt weg (8 → 2), die beiden Sport-Meldungen
    assert sorted(a.title for a in weg) == ["Bundesliga: Rapid verliert", "Rapid-Trainer entlassen"]
    # Rest behält seine Reihenfolge (stabil)
    assert [a.title for a in geordnet[1:3]] == ["Tesla-Klage in Wien", "Regierungskrise: Kanzler tritt zurück"]


def test_top_nachricht_wird_nie_weggelassen():
    profil = {"gewichte": {"wort:kanzler": -10.0, "wort:regieru": -10.0}}
    geordnet, weg = leserprofil.ordne_material(_material(), profil, TOPICS)
    assert weg == []
    assert any(a.title.startswith("Regierungskrise") for a in geordnet)


def test_hoechstens_ein_viertel_faellt_weg():
    profil = {"gewichte": {f"ressort:{r}": -5.0 for r in ("Wirtschaft", "Sport", "Recht", "Panorama", "Immobilien")}}
    _, weg = leserprofil.ordne_material(_material(), profil, TOPICS)
    assert len(weg) == 2


def test_prompt_block_nennt_plus_und_minus():
    block = leserprofil.prompt_block({"gewichte": {
        "thema:Mietrecht und Wohnkosten in Österreich": 1.2, "ressort:Sport": -0.8, "wort:tesla": -0.1,
    }})
    assert "Mietrecht und Wohnkosten" in block and "Ressort Sport" in block
    assert "tesla" not in block  # unter der Schwelle
    assert "Top-Nachrichten" in block


# ── Web-Feedback aus dem freien Zähler ───────────────────────────────────────

class _Antwort:
    def __init__(self, status, wert=None):
        self.status_code = status
        self._wert = wert

    def json(self):
        return {"value": self._wert}


def _fake_get(werte):
    def get(url, timeout=15):
        key = url.rsplit("/", 1)[-1]
        return _Antwort(200, werte[key]) if key in werte else _Antwort(404)
    return get


def test_web_votes_werden_einmal_uebernommen():
    s = {"edition_points": {"2026-11-21|morgen": ["Miete", "Ukraine"],
                            "2026-11-10|morgen": ["Alt"]},
         "punkt_merkmale": {"2026-11-21|morgen": [["ressort:Immobilien"], ["ressort:Ausland"]]}}
    get = _fake_get({"2026-11-21-morgen_fb0_up": 1, "2026-11-21-morgen_fb1_down": 2,
                     "2026-11-10-morgen_fb0_up": 5})
    assert leserprofil.sync_web_feedback(s, KONFIG_ZAEHLER, HEUTE, get) == 3
    # zweiter Lauf, gleiche Zählerstände → nichts Neues
    assert leserprofil.sync_web_feedback(s, KONFIG_ZAEHLER, HEUTE, get) == 0
    web = [e for e in s["article_feedback"] if e["quelle"] == "web"]
    assert sorted((e["article_idx"], e["rating"]) for e in web) == [(0, "up"), (1, "down"), (1, "down")]
    assert web[0]["merkmale"] in (["ressort:Immobilien"], ["ressort:Ausland"])
    g = leserprofil.berechne_profil(s, HEUTE)["gewichte"]
    assert g == {"ressort:Immobilien": 1.0, "ressort:Ausland": -2.0}


def test_web_sync_ohne_zaehler_oder_offline():
    s = {"edition_points": {"2026-11-21|morgen": ["Miete"]}}
    assert leserprofil.sync_web_feedback(s, {}, HEUTE, _fake_get({})) == 0

    def offline(url, timeout=15):
        raise OSError("offline")
    assert leserprofil.sync_web_feedback(s, KONFIG_ZAEHLER, HEUTE, offline) == 0
    assert "article_feedback" not in s


def test_browser_zaehlt_vote_je_punkt():
    from copilot import webview
    js = webview._PAGE_TEMPLATE
    assert "window.__zaehleVote(bar.dataset.key,vote)" in js
    assert "'fb'+idx+'_'+vote" in js
    assert leserprofil.vote_zaehler_key("2026-11-21", "morgen", 3, "up") == "2026-11-21-morgen_fb3_up"


# ── Ende-zu-Ende über den Dry-Run ────────────────────────────────────────────

CONFIG = {
    "editions": {"morgen": {"label": "Morgen", "time": "06:00", "lookback_hours": 24},
                 "mittag": {"label": "Mittag", "time": "11:00", "lookback_hours": 5}},
    "topics": TOPICS,
}


def _dry_run(monkeypatch, tmp_path, s):
    monkeypatch.setattr(main.state, "load_state", lambda: s)
    monkeypatch.setattr(main, "fetch_all", lambda config: FetchResult(articles=_material()))
    monkeypatch.setattr(render, "OUT_DIR", tmp_path)
    monkeypatch.setattr(synthesize, "load_manual_fulltexts", lambda: [])
    assert main.run_edition("morgen", CONFIG, dry_run=True, keep_seen=True) == 0
    return next(tmp_path.glob("*-morgen-prompt.txt")).read_text(encoding="utf-8")


def test_dry_run_ohne_feedback_wie_bisher(monkeypatch, tmp_path):
    prompt = _dry_run(monkeypatch, tmp_path, {})
    assert "Leserprofil" not in prompt
    titel = [a.title for a in _material()]
    positionen = [prompt.index(t) for t in titel]
    assert positionen == sorted(positionen)  # Feed-Reihenfolge unverändert


def test_dry_run_mit_feedback_steuert_material(monkeypatch, tmp_path):
    heute = datetime.now().date().isoformat()
    s = {"article_feedback": [
        _vote(heute, 0, "up", ["ressort:Immobilien"]),
        _vote(heute, 1, "down", ["ressort:Sport"], chat="2"),
        _vote(heute, 2, "down", ["ressort:Sport"], chat="3"),
        _vote(heute, 3, "down", ["ressort:Sport"], chat="4"),
    ]}
    prompt = _dry_run(monkeypatch, tmp_path, s)
    assert "# Leserprofil" in prompt and "Ressort Sport" in prompt
    material = prompt[prompt.index("# Material"):]
    assert "Rapid" not in material                         # abgewählt, kein Top-Thema
    assert "Regierungskrise" in material                   # Top-Nachricht bleibt
    assert material.index("Mietpreisbremse") < material.index("Tesla-Klage")
