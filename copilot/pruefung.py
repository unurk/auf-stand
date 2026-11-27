"""Täglicher Qualitätscheck der veröffentlichten Ausgabe (ersetzt die Bot-Prüfung).

Bis 30.11.2026 hat ein externer Bot jeden Morgen die 06-Uhr-Ausgabe gelesen und
Fehler gemeldet. Ab 1.12. übernimmt das dieser Check — deterministisch, ohne
API-Aufruf und ohne Secret. Er liest genau das, was die Leserin sieht
(``site/archiv/<datum>-<ausgabe>.html``), und prüft:

- Ausgabe da und pünktlich (erster Commit spätestens 90 Min. nach dem Slot)
- Schlagzeile und Punkt-Titel gegen den Text (Zahlen, Absicht, Wörter) — titelcheck
- Wochentage gegen Daten — zeittreue
- „Heute wichtig" spiegelt die Punkte
- jeder Punkt hat einen Quell-Link „Weiterlesen bei der Presse"
- Lesezeit im Budget

Der Workflow ``.github/workflows/qualitaet.yml`` legt bei Befund ein Issue an
(Label ``qualitaetscheck``) und schickt einen Telegram-Alarm.
"""
from __future__ import annotations

import html as _html
import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from . import slot, titelcheck, zeittreue

BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIV = BASE_DIR / "site" / "archiv"
MAX_VERSPAETUNG_MIN = 90


def _text(fragment: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def lies_ausgabe(seite: str) -> dict:
    """Zerlegt eine Archiv-Seite: Schlagzeile, Heute-wichtig, Punkte, Lesezeit."""
    h1 = re.search(r"<h1>(.*?)</h1>", seite, re.DOTALL)
    hl = re.search(r'<div class="highlights">(.*?)</div>', seite, re.DOTALL)
    heute_wichtig = []
    if hl:
        heute_wichtig = [_text(p) for p in re.findall(r"<p>(.*?)</p>", hl.group(1), re.DOTALL)
                         if "<strong>" not in p]
    punkte = []
    for teil in re.split(r"(?=<h2>)", seite)[1:]:
        if 'class="article-fb"' not in teil:
            continue  # Themen-/Prüf-Abschnitte haben keine Feedback-Leiste
        teil = teil.split('<div class="article-fb"')[0]
        titel = _text(re.search(r"<h2>(.*?)</h2>", teil, re.DOTALL).group(1))
        zeilen = []
        for p in re.findall(r"<p[^>]*>(.*?)</p>", teil, re.DOTALL):
            p = re.sub(r"<strong>(.*?)</strong>", r"**\1**", p)
            zeilen.append(_text(p))
        quelle = re.search(r'class="source-link" href="([^"]+)"', teil)
        punkte.append({"titel": titel, "zeilen": zeilen,
                       "quelle": quelle.group(1) if quelle else ""})
    lesezeit = re.search(r"Lesezeit ca\.\s*(\d+)\s*Sekunden", seite)
    return {
        "h1": _text(h1.group(1)) if h1 else "",
        "heute_wichtig": heute_wichtig,
        "punkte": punkte,
        "lesezeit": int(lesezeit.group(1)) if lesezeit else None,
    }


def als_markdown(ausgabe: dict) -> str:
    """Rekonstruiert das Markdown-Format, das titelcheck/zeittreue erwarten."""
    teile = [f"# ☀️ {ausgabe['h1']}", ""]
    for n, p in enumerate(ausgabe["punkte"], 1):
        teile.append(f"## {n}️⃣ 📰 {p['titel']}")
        teile.extend(p["zeilen"])
        teile.append("")
    return "\n".join(teile)


def _slug_woerter(text: str) -> set[str]:
    t = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return {w for w in re.findall(r"[a-z0-9]+", t) if len(w) >= 3}


def ist_quell_schlagzeile(titel: str, url: str) -> bool:
    """Entspricht der Titel der Presse-Schlagzeile (URL-Slug des Quell-Links)?"""
    if not url:
        return False
    slug = _slug_woerter(url.rstrip("/").rsplit("/", 1)[-1])
    woerter = _slug_woerter(titel)
    return bool(woerter) and len(woerter & slug) / len(woerter) >= 0.8


def erster_commit(pfad: Path) -> datetime | None:
    """Zeitpunkt, zu dem die Datei erstmals committet wurde (= veröffentlicht)."""
    try:
        out = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%cI", "--", str(pfad)],
            cwd=BASE_DIR, capture_output=True, text=True, check=True,
        ).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return None
    return datetime.fromisoformat(out[-1]) if out else None


def pruefe(datum: date, ausgabe: str, config: dict, archiv: Path = ARCHIV,
           commit_zeit=erster_commit) -> list[str]:
    """Alle Befunde zur Ausgabe — leere Liste = alles in Ordnung."""
    befunde: list[str] = []
    pfad = archiv / f"{datum.isoformat()}-{ausgabe}.html"
    if not pfad.exists():
        return [f"Ausgabe fehlt: {pfad.name} ist nicht im Archiv (nicht erzeugt oder nicht committet)."]

    zeit = (config.get("editions", {}).get(ausgabe) or {}).get("time", "06:00")
    h, m = (int(x) for x in zeit.split(":"))
    termin = datetime(datum.year, datum.month, datum.day, h, m, tzinfo=slot.WIEN)
    veroeffentlicht = commit_zeit(pfad)
    if veroeffentlicht is not None:
        spaet = veroeffentlicht.astimezone(slot.WIEN) - termin
        if spaet > timedelta(minutes=MAX_VERSPAETUNG_MIN):
            befunde.append(
                f"Verspätet: veröffentlicht {veroeffentlicht.astimezone(slot.WIEN):%H:%M} Uhr, "
                f"Slot {zeit} Uhr ({int(spaet.total_seconds() // 60)} Min. zu spät)."
            )
        elif spaet < -timedelta(hours=2):
            befunde.append(
                f"Zu früh: veröffentlicht {veroeffentlicht.astimezone(slot.WIEN):%d.%m. %H:%M} Uhr "
                f"für den {zeit}-Uhr-Slot — falscher Slot?"
            )

    a = lies_ausgabe(pfad.read_text(encoding="utf-8"))
    punkte = a["punkte"]
    if not punkte:
        return befunde  # Ruhe-Ausgabe: nichts weiter zu prüfen

    md = als_markdown(a)
    _, korrekturen = titelcheck.pruefe_titel(md, [])
    # Hat die Pipeline den Titel schon durch die Presse-Schlagzeile ersetzt
    # (Absicht → Quell-Schlagzeile), ist er redaktionell geprüft — kein Befund.
    presse = {n for n, p in enumerate(punkte, 1) if ist_quell_schlagzeile(p["titel"], p["quelle"])}
    korrekturen = [
        k for k in korrekturen
        if not (re.match(r"Punkt (\d+): Absicht", k) and int(re.match(r"Punkt (\d+)", k).group(1)) in presse)
        and not (k.startswith("H1: Absicht in Punkt 1") and 1 in presse)
    ]
    befunde.extend(f"Titel: {k}" for k in korrekturen)
    _, wochentage = zeittreue.pruefe_wochentage(md, datum)
    befunde.extend(f"Wochentag: {k}" for k in wochentage)

    titel = [p["titel"] for p in punkte]
    if a["heute_wichtig"] and a["heute_wichtig"] != titel:
        befunde.append(f"„Heute wichtig“ ({len(a['heute_wichtig'])} Zeilen) spiegelt die "
                       f"{len(titel)} Punkte nicht.")
    for n, p in enumerate(punkte, 1):
        if not p["quelle"]:
            befunde.append(f"Quell-Link fehlt bei Punkt {n} („{p['titel']}“).")

    budget = int(config.get("lesezeit_budget_sekunden", 90))
    if a["lesezeit"] is not None and a["lesezeit"] > budget:
        befunde.append(f"Lesezeit {a['lesezeit']} s über dem Budget von {budget} s.")
    return befunde


def bericht(datum: date, ausgabe: str, befunde: list[str]) -> str:
    """Issue-Text: Befunde + Arbeitsauftrag für die nächste Claude-Code-Session."""
    zeilen = [
        f"Automatischer Qualitätscheck der Ausgabe **{ausgabe} {datum:%d.%m.%Y}** "
        f"(`site/archiv/{datum.isoformat()}-{ausgabe}.html`).",
        "",
        "## Befunde",
        *[f"- {b}" for b in befunde],
        "",
        "## Auftrag",
        "Ursache im Code finden und belegen (Lauf-Log), deterministisch beheben, "
        "Regressionstest mit genau diesem Fall, PR gegen master. Regeln: siehe UEBERGABE.md.",
    ]
    return "\n".join(zeilen)


def cmd_pruefen(config: dict, datum: str | None, ausgabe: str, ausgabe_datei: str | None) -> int:
    """CLI: schreibt den Bericht (bei Befund) in eine Datei, sonst nichts. Exit 0."""
    tag = date.fromisoformat(datum) if datum else datetime.now(slot.WIEN).date()
    befunde = pruefe(tag, ausgabe, config)
    if not befunde:
        print(f"Qualitätscheck {ausgabe} {tag}: keine Befunde.")
        return 0
    text = bericht(tag, ausgabe, befunde)
    print(text)
    if ausgabe_datei:
        Path(ausgabe_datei).write_text(text, encoding="utf-8")
    return 0
