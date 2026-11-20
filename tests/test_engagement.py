"""Engagement-Messung: Öffnungen je Ausgabe (Web + Telegram) und Feedback-Rate."""
from datetime import date

from copilot import engagement, webview

HEUTE = date(2026, 11, 21)  # Samstag → Zeitraum Sa 14.11. – Fr 20.11.
KONFIG = {"engagement": {"zaehler_url": "https://zaehler.example", "namespace": "auf-stand-test"}}


def _state():
    stats = [
        {"date": f"2026-11-{t:02d}", "edition": e}
        for t in range(14, 21) for e in ("morgen", "mittag", "nachmittag", "abend")
    ]
    stats.append({"date": "2026-11-13", "edition": "morgen"})  # außerhalb
    stats.append({"date": "2026-11-20", "edition": "catchup"})  # kein Slot
    return {
        "stats": stats,
        "read_events": [
            {"for_date": "2026-11-20", "edition": "morgen", "quelle": "telegram_tap"},
            {"for_date": "2026-11-19", "edition": "abend", "quelle": "artfb"},
            {"for_date": "", "edition": "", "quelle": "gelesen"},  # nicht zuordenbar
        ],
        "feedback": [{"date": "2026-11-19", "edition": "abend", "rating": "up"}],
        "article_feedback": [
            {"date": "2026-11-19", "edition": "abend", "article_idx": 0, "rating": "up"},
            {"date": "2026-11-18", "edition": "mittag", "article_idx": 1, "rating": "down"},
        ],
    }


class _Antwort:
    def __init__(self, status, wert=None):
        self.status_code, self._wert = status, wert

    def json(self):
        return {"value": self._wert}


def _fake_get(werte: dict):
    """URL-Endung → (Status, Wert); unbekannte Schlüssel = 400 (nie getroffen)."""
    aufrufe = []

    def get(url, timeout=15):
        aufrufe.append(url)
        for endung, (status, wert) in werte.items():
            if url.endswith(endung):
                return _Antwort(status, wert)
        return _Antwort(400)

    get.aufrufe = aufrufe
    return get


# ── Konfiguration ────────────────────────────────────────────────────────────

def test_ohne_konfiguration_kein_zaehler():
    assert engagement.zaehler_config({}) is None
    assert engagement.zaehler_config({"engagement": {"zaehler_url": "http://x", "namespace": "abc"}}) is None
    assert engagement.zaehler_config({"engagement": {"zaehler_url": "https://x", "namespace": ""}}) is None
    assert engagement.zaehler_config(KONFIG) == ("https://zaehler.example", "auf-stand-test")


def test_schluessel_wie_im_browser():
    assert engagement.zaehler_key("2026-11-20", "morgen", "offen") == "2026-11-20-morgen_offen"


# ── Telegram ─────────────────────────────────────────────────────────────────

def test_telegram_taps_zaehlen_als_oeffnung_und_feedback():
    offen, fb, taps = engagement.telegram_signale(_state(), engagement.zeitraum(HEUTE))
    assert offen == {("2026-11-20", "morgen"), ("2026-11-19", "abend"), ("2026-11-18", "mittag")}
    assert fb == {("2026-11-19", "abend"), ("2026-11-18", "mittag")}
    assert taps == 3


# ── Web-Zähler ───────────────────────────────────────────────────────────────

def test_lies_zaehler_status_codes():
    get = _fake_get({"/ok": (200, 3), "/fehlt": (404, None), "/kaputt": (500, None)})
    assert engagement.lies_zaehler("https://z", "ns", "ok", get) == 3
    assert engagement.lies_zaehler("https://z", "ns", "fehlt", get) == 0
    assert engagement.lies_zaehler("https://z", "ns", "nie", get) == 0      # 400
    assert engagement.lies_zaehler("https://z", "ns", "kaputt", get) is None

    def explodiert(url, timeout=15):
        raise OSError("offline")
    assert engagement.lies_zaehler("https://z", "ns", "x", explodiert) is None


def test_lies_zaehler_wartet_bei_rate_limit_einmal():
    antworten = iter([_Antwort(429), _Antwort(200, 2)])
    pausen = []
    wert = engagement.lies_zaehler("https://z", "ns", "k", lambda u, timeout=15: next(antworten),
                                   pausen.append)
    assert wert == 2 and pausen == [10]


def test_web_ohne_konfiguration_ist_no_op():
    get = _fake_get({})
    assert engagement.web_signale({("2026-11-20", "morgen")}, {}, get, lambda s: None) is None
    assert get.aufrufe == []


# ── Auswertung ───────────────────────────────────────────────────────────────

def _auswertung(web_werte=None, config=KONFIG):
    tage = engagement.zeitraum(HEUTE)
    state = _state()
    get = _fake_get(web_werte or {})
    web = engagement.web_signale(engagement.ausgaben_im_zeitraum(state, tage), config, get, lambda s: None)
    return engagement.auswerten(state, tage, web), get


def test_oeffnungen_je_ausgabe_web_und_telegram():
    a, get = _auswertung({
        "2026-11-20-morgen_offen": (200, 1),     # Web + Telegram → 1 Öffnung
        "2026-11-20-mittag_offen": (200, 2),     # zwei Geräte → trotzdem 1 Ausgabe
        "2026-11-17-nachmittag_offen": (200, 1),
        "2026-11-17-nachmittag_fb": (200, 2),    # Web-Feedback zu 2 Artikeln
    })
    assert a["geliefert"] == 28
    assert a["offen"] == 5
    slots = {s["edition"]: s for s in a["slots"]}
    assert slots["morgen"] == {"edition": "morgen", "uhr": "06", "geliefert": 7, "offen": 1,
                               "web": 1, "telegram": 1, "feedback": 0}
    assert slots["mittag"]["offen"] == 2 and slots["abend"]["offen"] == 1
    assert slots["nachmittag"]["feedback"] == 1
    assert a["feedback"] == 3 and a["feedback_taps"] == 5
    assert len(get.aufrufe) == 56  # 28 Ausgaben × (offen, fb)


def test_bericht_enthaelt_kennzahlen_und_matrix():
    a, _ = _auswertung({"2026-11-20-morgen_offen": (200, 1)})
    md = engagement.bericht_markdown(a)
    assert "## Woche 14.11.–20.11.2026" in md
    assert "**Geöffnet:** 3 von 28 Ausgaben (11 %)" in md
    assert "**Feedback-Rate:** 67 % (2 von 3 geöffneten Ausgaben, 3 Taps)" in md
    assert "| 06 Uhr | 7 | 1 | 14 % | 1 | 1 | 0 | 0 % |" in md
    assert "| Fr 20.11. | ✓WT | – | – | – |" in md
    assert "| Do 19.11. | – | – | – | ✓T💬 |" in md


def test_bericht_ohne_web_zaehler_nur_telegram():
    a, get = _auswertung(config={})
    md = engagement.bericht_markdown(a)
    assert get.aufrufe == []
    assert "Web-Zähler nicht konfiguriert" in md
    assert "| 06 Uhr | 7 | 1 | 14 % | – | 1 | 0 | 0 % |" in md


def test_unerreichbarer_web_zaehler_wird_markiert():
    def offline(url, timeout=15):
        raise OSError
    tage = engagement.zeitraum(HEUTE)
    web = engagement.web_signale({("2026-11-16", "morgen")}, KONFIG, offline, lambda s: None)
    a = engagement.auswerten(_state(), tage, web)
    assert "?" in dict(a["matrix"])[date(2026, 11, 16)]
    assert "nicht erreichbar" in engagement.bericht_markdown(a)


# ── Bericht-Datei ────────────────────────────────────────────────────────────

def test_bericht_datei_neueste_woche_oben_und_idempotent(tmp_path):
    pfad = tmp_path / "engagement.md"
    engagement.schreibe_bericht("## Woche A\n", "a", pfad)
    engagement.schreibe_bericht("## Woche B\n", "b", pfad)
    engagement.schreibe_bericht("## Woche B neu\n", "b", pfad)  # gleiche Woche → ersetzt
    text = pfad.read_text(encoding="utf-8")
    assert text.startswith("# Engagement")
    assert text.index("Woche B neu") < text.index("Woche A")
    assert text.count("<!-- woche:b -->") == 1 and "## Woche B\n" not in text


def test_bericht_datei_behaelt_hoechstens_max_wochen(tmp_path):
    pfad = tmp_path / "engagement.md"
    for i in range(5):
        engagement.schreibe_bericht(f"## Woche {i}\n", str(i), pfad, max_wochen=3)
    text = pfad.read_text(encoding="utf-8")
    assert "Woche 4" in text and "Woche 2" in text and "Woche 1" not in text


def test_cmd_dry_run_schreibt_nichts(tmp_path):
    pfad = tmp_path / "engagement.md"
    rc = engagement.cmd_engagement({}, _state(), dry_run=True, heute=HEUTE, pfad=pfad)
    assert rc == 0 and not pfad.exists()
    engagement.cmd_engagement({}, _state(), heute=HEUTE, pfad=pfad)
    assert "## Woche 14.11.–20.11.2026" in pfad.read_text(encoding="utf-8")


# ── Web-Seite ────────────────────────────────────────────────────────────────

def test_seitenkopf_traegt_ausgaben_id():
    kopf = webview._lagebild_header("2026-11-20", "morgen", 3, 90, "de", "Schlagzeile")
    assert '<header class="lagebild-header" data-ausgabe="2026-11-20-morgen">' in kopf


def test_zaehler_skript_nur_mit_konfiguration():
    assert webview._zaehler_script({}) == ""
    skript = webview._zaehler_script(KONFIG)
    assert 'window.__ZAEHLER__={"base": "https://zaehler.example", "ns": "auf-stand-test"}' in skript


def test_seiten_js_zaehlt_cookie_frei_und_einmal_je_ausgabe():
    js = webview._PAGE_TEMPLATE
    assert "credentials:'omit'" in js and "referrerPolicy:'no-referrer'" in js
    assert "einmal('zaehler_offen_'+id,'offen')" in js
    assert "window.__zaehleFeedback(bar.dataset.key)" in js
    assert "if(!z||!z.base||!z.ns||!head) return;" in js  # ohne Konfiguration no-op


def test_archiv_neubau_ersetzt_kopf_mit_attribut():
    """Der Kopf trägt jetzt ein Attribut — der Neubau muss ihn trotzdem finden."""
    html = webview._lagebild_header("2026-11-20", "morgen", 1, 90, "de", "A") + "<h2>A</h2><p>x</p><hr>"
    einmal = webview._enhance_content(html, "2026-11-20", "morgen", "de")
    assert einmal.count("<header") == 1
    assert webview._enhance_content(einmal, "2026-11-20", "morgen", "de") == einmal


def test_leere_woche_mit_konfiguriertem_zaehler_meldet_nicht_unkonfiguriert():
    a = engagement.auswerten({}, engagement.zeitraum(HEUTE), {})
    assert "nicht konfiguriert" not in engagement.bericht_markdown(a)


def test_stoerungsantwort_mit_status_200_ist_kein_null_wert():
    class _Fehler:
        status_code = 200

        def json(self):
            return {"error": "Failed to get data. Try again later."}

    assert engagement.lies_zaehler("https://z", "ns", "k", lambda u, timeout=15: _Fehler()) is None


def test_service_worker_cacht_zaehler_requests_nicht():
    """Der Cache-first-Zweig für fremde Origins hätte Zähler-Requests verschluckt."""
    sw = webview._SERVICE_WORKER
    assert sw.index("if(req.cache === 'no-store') return;") < sw.index("url.origin !== self.location.origin")
    assert "cache:'no-store'" in webview._PAGE_TEMPLATE
