"""Engagement-Messung: Wird jede Ausgabe geöffnet, und wie oft kommt Feedback?

Kennzahlen je Ausgabe-Slot (06 · 11 · 16 · 20 Uhr Wien), wöchentlich:
- Öffnungen: Web (cookie-freier Zähler, eine Zählung je Gerät und Ausgabe)
  ∪ Telegram (Tap auf „✓ Gelesen" oder ein 👍/👎 — Telegram meldet Bots kein
  „gelesen", ein Tap ist das einzige Signal).
- Feedback-Rate: Anteil der geöffneten Ausgaben mit mindestens einem Feedback
  (Web „Relevant"/„Weniger" oder Telegram 👍/👎).

Quellen, alle ohne neues Secret und ohne kostenpflichtigen Dienst:
- Telegram: data/state.json — der Rückkanal-Schritt der Action sammelt die
  Button-Taps ohnehin ein (vorhandenes TELEGRAM_BOT_TOKEN).
- Web: Abacus (abacus.jasoncameron.dev), ein freier Zähl-Endpunkt ohne Account,
  ohne Cookies, ohne Token. Die Seite schickt nur „/hit/<namespace>/<ausgabe>_offen";
  gelesen wird hier mit „/get/…". Ist kein Zähler konfiguriert, entfällt die
  Web-Spalte (no-op), der Rest läuft weiter.

Die Auswertung landet in berichte/engagement.md (neueste Woche oben). Sie
enthält nur Zählwerte je Ausgabe, keine Uhrzeiten oder Geräte.
"""
from __future__ import annotations

import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

SLOTS = [("morgen", "06"), ("mittag", "11"), ("nachmittag", "16"), ("abend", "20")]
_SLOT_NAMEN = {e for e, _ in SLOTS}
BERICHT_PFAD = Path(__file__).resolve().parent.parent / "berichte" / "engagement.md"
MAX_WOCHEN = 12
_WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def zaehler_config(config: dict) -> tuple[str, str] | None:
    """(Basis-URL, Namespace) des Web-Zählers — None, wenn nicht konfiguriert."""
    eng = (config or {}).get("engagement") or {}
    base = str(eng.get("zaehler_url") or "").rstrip("/")
    ns = str(eng.get("namespace") or "")
    if not base.startswith("https://") or not re.fullmatch(r"[A-Za-z0-9_.-]{3,64}", ns):
        return None
    return base, ns


def zaehler_key(datum: str, edition: str, art: str) -> str:
    """Schlüssel wie im Browser: „2026-11-20-morgen_offen"."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", f"{datum}-{edition}") + f"_{art}"


def lies_zaehler(base: str, ns: str, key: str, http_get=None, pause=time.sleep) -> int | None:
    """Zählerstand; 0, wenn der Zähler nie getroffen wurde; None bei Fehler."""
    if http_get is None:
        import httpx
        http_get = httpx.get
    url = f"{base}/get/{ns}/{key}"
    for versuch in range(2):
        try:
            r = http_get(url, timeout=15)
        except Exception:
            return None
        if r.status_code == 429 and versuch == 0:  # Rate-Limit (30 Anfragen / 10 s)
            pause(10)
            continue
        if r.status_code in (400, 404):  # Schlüssel existiert nicht = nie geöffnet
            return 0
        if r.status_code != 200:
            return None
        try:
            daten = r.json()
            # Abacus meldet Störungen teils mit 200 + {"error": …} — kein Wert ≠ 0.
            return int(daten["value"]) if "value" in daten else None
        except (ValueError, AttributeError, TypeError, KeyError):
            return None
    return None


def zeitraum(heute: date, tage: int = 7) -> list[date]:
    """Die `tage` Tage bis einschließlich gestern (Samstags-Lauf: Sa–Fr)."""
    return [heute - timedelta(days=i) for i in range(tage, 0, -1)]


def ausgaben_im_zeitraum(state: dict, tage: list[date]) -> set[tuple[str, str]]:
    """Ausgelieferte Ausgaben (Datum, Slot) laut stats."""
    gueltig = {d.isoformat() for d in tage}
    return {
        (s.get("date", ""), s.get("edition", ""))
        for s in state.get("stats", [])
        if s.get("date") in gueltig and s.get("edition") in _SLOT_NAMEN
    }


def telegram_signale(state: dict, tage: list[date]) -> tuple[set, set, int]:
    """(geöffnet, mit Feedback, Anzahl Feedback-Taps) aus dem Telegram-Rückkanal."""
    gueltig = {d.isoformat() for d in tage}
    offen = {
        (e.get("for_date", ""), e.get("edition", ""))
        for e in state.get("read_events", [])
        if e.get("for_date") in gueltig and e.get("edition") in _SLOT_NAMEN
    }
    fb_eintraege = [
        e for e in state.get("feedback", []) + state.get("article_feedback", [])
        if e.get("date") in gueltig and e.get("edition") in _SLOT_NAMEN
    ]
    fb = {(e["date"], e["edition"]) for e in fb_eintraege}
    return offen | fb, fb, len(fb_eintraege)


def web_signale(
    ausgaben: set[tuple[str, str]], config: dict, http_get=None, pause=time.sleep,
) -> dict | None:
    """{(datum, slot): {"offen": n|None, "fb": n|None}} — None ohne Zähler-Konfiguration."""
    zc = zaehler_config(config)
    if zc is None:
        return None
    base, ns = zc
    werte = {}
    for datum, edition in sorted(ausgaben):
        eintrag = {}
        for art in ("offen", "fb"):
            eintrag[art] = lies_zaehler(base, ns, zaehler_key(datum, edition, art), http_get, pause)
            pause(0.4)  # unter dem Rate-Limit bleiben
        werte[(datum, edition)] = eintrag
    return werte


def auswerten(state: dict, tage: list[date], web: dict | None) -> dict:
    """Verdichtet alle Signale zu Kennzahlen je Slot und einer Tages-Matrix."""
    tg_offen, tg_fb, tg_fb_taps = telegram_signale(state, tage)
    web_aktiv = web is not None
    web = web or {}
    web_offen = {k for k, v in web.items() if (v.get("offen") or 0) > 0}
    web_fb = {k for k, v in web.items() if (v.get("fb") or 0) > 0}
    web_unbekannt = {k for k, v in web.items() if v.get("offen") is None}
    web_fb_taps = sum((v.get("fb") or 0) for v in web.values())
    offen = tg_offen | web_offen
    # Wer öffnet, hat eine Ausgabe bekommen — auch wenn stats fehlen (Cache-Verlust).
    geliefert = ausgaben_im_zeitraum(state, tage) | offen
    mit_fb = tg_fb | web_fb

    slots = []
    for edition, uhr in SLOTS:
        g = {k for k in geliefert if k[1] == edition}
        o = {k for k in offen if k[1] == edition}
        f = {k for k in mit_fb if k[1] == edition}
        slots.append({
            "edition": edition, "uhr": uhr, "geliefert": len(g), "offen": len(o),
            "web": len(o & web_offen), "telegram": len(o & tg_offen), "feedback": len(f),
        })
    matrix = []
    for d in tage:
        zeile = []
        for edition, _ in SLOTS:
            k = (d.isoformat(), edition)
            if k not in geliefert:
                zeile.append("·")
            elif k in offen:
                quelle = ("W" if k in web_offen else "") + ("T" if k in tg_offen else "")
                zeile.append("✓" + quelle + ("💬" if k in mit_fb else ""))
            elif k in web_unbekannt:
                zeile.append("?")
            else:
                zeile.append("–")
        matrix.append((d, zeile))
    return {
        "tage": tage, "slots": slots, "matrix": matrix,
        "geliefert": len(geliefert), "offen": len(offen), "feedback": len(mit_fb),
        "feedback_taps": tg_fb_taps + web_fb_taps,
        "web_aktiv": web_aktiv, "web_fehler": len(web_unbekannt),
    }


def _quote(teil: int, ganz: int) -> str:
    return f"{round(100 * teil / ganz)} %" if ganz else "–"


def bericht_markdown(a: dict) -> str:
    tage = a["tage"]
    von, bis = tage[0], tage[-1]
    zeilen = [
        f"## Woche {von:%d.%m.}–{bis:%d.%m.%Y}",
        "",
        f"**Geöffnet:** {a['offen']} von {a['geliefert']} Ausgaben "
        f"({_quote(a['offen'], a['geliefert'])}) · "
        f"**Feedback-Rate:** {_quote(a['feedback'], a['offen'])} "
        f"({a['feedback']} von {a['offen']} geöffneten Ausgaben, {a['feedback_taps']} Taps)",
        "",
        "| Ausgabe | geliefert | geöffnet | Quote | davon Web | davon Telegram | mit Feedback | Feedback-Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for s in a["slots"]:
        zeilen.append(
            f"| {s['uhr']} Uhr | {s['geliefert']} | {s['offen']} | {_quote(s['offen'], s['geliefert'])} "
            f"| {s['web'] if a['web_aktiv'] else '–'} | {s['telegram']} | {s['feedback']} "
            f"| {_quote(s['feedback'], s['offen'])} |"
        )
    zeilen += ["", "| Tag | 06 | 11 | 16 | 20 |", "|---|:-:|:-:|:-:|:-:|"]
    for d, felder in a["matrix"]:
        zeilen.append(f"| {_WOCHENTAGE[d.weekday()]} {d:%d.%m.} | " + " | ".join(felder) + " |")
    hinweise = ["✓ geöffnet (W = Web, T = Telegram) · 💬 mit Feedback · – nicht geöffnet · · nicht ausgeliefert"]
    if not a["web_aktiv"]:
        hinweise.append("Web-Zähler nicht konfiguriert (config.yaml → engagement) — nur Telegram gezählt.")
    elif a["web_fehler"]:
        hinweise.append(f"? = Web-Zähler für {a['web_fehler']} Ausgabe(n) nicht erreichbar.")
    hinweise.append("Telegram meldet Bots kein „gelesen“ — dort zählt nur ein Tap (✓ Gelesen, 👍/👎).")
    zeilen += [""] + [f"_{h}_  " for h in hinweise]
    return "\n".join(zeilen).rstrip() + "\n"


_KOPF = (
    "# Engagement — Öffnungen und Feedback je Ausgabe\n\n"
    "Wöchentlich automatisch erzeugt (GitHub Action, Samstag) aus Telegram-Taps und "
    "dem cookie-freien Web-Zähler. Siehe `copilot/engagement.py`.\n"
)


def schreibe_bericht(abschnitt: str, woche_id: str, pfad: Path = BERICHT_PFAD,
                     max_wochen: int = MAX_WOCHEN) -> Path:
    """Setzt die Woche oben ein (ersetzt sie bei erneutem Lauf), behält max_wochen."""
    marker = f"<!-- woche:{woche_id} -->"
    bloecke: list[tuple[str, str]] = []
    if pfad.exists():
        alt = pfad.read_text(encoding="utf-8")
        for m in re.finditer(r"<!-- woche:(\S+) -->\n(.*?)(?=<!-- woche:|\Z)", alt, re.DOTALL):
            if m.group(1) != woche_id:
                bloecke.append((m.group(1), m.group(2).strip() + "\n"))
    bloecke.insert(0, (woche_id, abschnitt))
    teile = [_KOPF] + [f"<!-- woche:{w} -->\n{b}" for w, b in bloecke[:max_wochen]]
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text("\n".join(teile), encoding="utf-8")
    return pfad


def cmd_engagement(config: dict, state: dict, dry_run: bool = False, heute: date | None = None,
                   http_get=None, pause=time.sleep, pfad: Path = BERICHT_PFAD) -> int:
    heute = heute or datetime.now().date()
    tage = zeitraum(heute)
    geliefert = ausgaben_im_zeitraum(state, tage)
    web = web_signale(geliefert, config, http_get, pause)
    auswertung = auswerten(state, tage, web)
    abschnitt = bericht_markdown(auswertung)
    print(abschnitt)
    if dry_run:
        print("Dry-Run: Auswertung nicht gespeichert.")
        return 0
    ziel = schreibe_bericht(abschnitt, f"{tage[0].isoformat()}..{tage[-1].isoformat()}", pfad)
    print(f"Engagement-Auswertung gespeichert: {ziel}")
    return 0
