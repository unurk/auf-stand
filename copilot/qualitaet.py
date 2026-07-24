"""Qualitäts-Gate: hält die Ausgabe deterministisch im Zeitbudget.

Der Prompt formuliert die Regeln, aber ein Sprachmodell hält sie nicht zuverlässig
ein — im Archiv lag die Lesezeit im Median bei 120 s (Ziel: ~90 s), und der
Abschnitt „Deine Themen" wuchs auf bis zu neun Zeilen, darunter mehrfach ein
ausdrückliches „hat sich nichts Wesentliches getan" (genau das verbietet
prompts/lagebild.md). Dieses Modul zieht die Regeln nach der Synthese hart nach:
leere Tracker-Deltas fliegen raus, der Tracker-Abschnitt wird gekappt.

Bewusst konservativ: gekürzt wird nur der Tracker-Abschnitt (Zusatz), nie ein
Hauptpunkt — die redaktionelle Auswahl bleibt beim Prompt.
"""
from __future__ import annotations

import re

# Formulierungen, die eine Tracker-Zeile als inhaltsleer ausweisen. Bewusst eng
# gefasst: nur Wendungen, die das Fehlen einer Änderung explizit benennen.
_LEER_PATTERNS = [
    r"nichts (?:wesentliches|neues|substanzielles)",
    r"nichts (?:getan|geändert|verändert|bewegt)",
    r"keine (?:materielle|wesentliche|substanzielle|nennenswerte|neue)n? (?:änderung|entwicklung|neuigkeit)",
    r"kein(?:e)? (?:handlungsbedarf|neuigkeiten|änderung)",
    r"zu keiner? (?:materiellen|wesentlichen) (?:änderung|gesetzesänderung|entwicklung)",
    r"(?:bleibt|blieb) (?:es )?(?:bei|unverändert)",
    r"unverändert",
    r"keine (?:neuen )?(?:meldungen|informationen)",
    r"no (?:material|substantive|significant) (?:change|development)",
    r"nothing (?:material|new|substantial)",
    r"remains unchanged",
]
_LEER_RE = re.compile("|".join(_LEER_PATTERNS), re.IGNORECASE)

MAX_TRACKER_ZEILEN = 3
MAX_TRACKER_WOERTER = 32


def ist_leeres_delta(zeile: str) -> bool:
    """True, wenn die Tracker-Zeile sagt „hat sich nichts geändert"."""
    return bool(_LEER_RE.search(zeile))


def _kuerze_zeile(zeile: str, max_woerter: int = MAX_TRACKER_WOERTER) -> str:
    """Kappt eine zu lange Tracker-Zeile am letzten Satzende im Budget."""
    woerter = zeile.split()
    if len(woerter) <= max_woerter:
        return zeile
    gekappt = " ".join(woerter[:max_woerter])
    # Bevorzugt am letzten abgeschlossenen Satz enden, sonst hart mit „…".
    m = list(re.finditer(r"[.!?](?=\s|$)", gekappt))
    if m and m[-1].end() > len(gekappt) * 0.5:
        return gekappt[: m[-1].end()]
    return gekappt.rstrip(" ,;–—") + " …"


def trim_tracker_section(
    markdown: str,
    heading: str = "Deine Themen",
    max_zeilen: int = MAX_TRACKER_ZEILEN,
) -> tuple[str, dict]:
    """Räumt den Themen-Abschnitt auf. Liefert (markdown, report).

    - Zeilen ohne materielle Änderung werden entfernt (Produktregel).
    - Es bleiben höchstens `max_zeilen` Zeilen stehen (Reihenfolge = Priorität
      des Modells).
    - Überlange Zeilen werden auf MAX_TRACKER_WOERTER gekürzt.
    - Bleibt keine Zeile übrig, entfällt die Überschrift mit.
    """
    lines = markdown.splitlines()
    start = next(
        (i for i, l in enumerate(lines) if l.startswith("## ") and heading in l), None
    )
    if start is None:
        return markdown, {"entfernt": 0, "gekappt": 0, "behalten": 0}

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") or lines[i].startswith("---"):
            end = i
            break

    behalten: list[str] = []
    entfernt = gekappt = 0
    for raw in lines[start + 1 : end]:
        zeile = raw.rstrip()
        if not zeile.strip():
            continue
        if not zeile.lstrip().startswith(("-", "*", "•")):
            behalten.append(zeile)  # Fließtext im Abschnitt unangetastet lassen
            continue
        if ist_leeres_delta(zeile):
            entfernt += 1
            continue
        if len(behalten) >= max_zeilen:
            entfernt += 1
            continue
        neu = _kuerze_zeile(zeile)
        if neu != zeile:
            gekappt += 1
        behalten.append(neu)

    hat_deltas = any(l.lstrip().startswith(("-", "*", "•")) for l in behalten)
    neue_lines = lines[:start]
    if hat_deltas:
        neue_lines.append(lines[start])
        neue_lines.extend(behalten)
        neue_lines.append("")
    neue_lines.extend(lines[end:])
    report = {"entfernt": entfernt, "gekappt": gekappt, "behalten": len(behalten)}
    return "\n".join(neue_lines), report


def lesezeit_sekunden(markdown: str, woerter_pro_sekunde: float = 3.2) -> int:
    """Lesezeit in Sekunden, auf 15 s gerundet (gleiche Formel wie main.py)."""
    woerter = len(re.findall(r"\w+", markdown))
    return max(60, round(woerter / woerter_pro_sekunde / 15) * 15)


def pruefe_budget(markdown: str, budget_sekunden: int, woerter_pro_sekunde: float = 3.2) -> str:
    """Warnhinweis, wenn die Ausgabe das Zeitbudget reißt — sonst ''.

    Bewusst nur eine Warnung im Log und ein Kalibrierungs-Hinweis für den
    nächsten Prompt: Kürzen würde Inhalt zerstören, den die Redaktion (das
    Modell) bewusst gesetzt hat. Der Hebel liegt im nächsten Lauf.
    """
    secs = lesezeit_sekunden(markdown, woerter_pro_sekunde)
    if secs <= budget_sekunden:
        return ""
    return (
        f"⚠️ Lesezeit-Budget gerissen: {secs} s statt {budget_sekunden} s — "
        "nächste Ausgabe straffer fassen (kürzere Punkte 3–5, weniger Nebensätze)."
    )


def budget_hinweis(letzte_sekunden: list[int], budget_sekunden: int) -> str:
    """Kalibrierungs-Block für den Prompt, wenn zuletzt zu lang geliefert wurde."""
    werte = [s for s in letzte_sekunden if s]
    if len(werte) < 3:
        return ""
    schnitt = round(sum(werte) / len(werte))
    if schnitt <= budget_sekunden:
        return ""
    return (
        f"⚠️ Länge: Die letzten {len(werte)} Ausgaben lagen im Schnitt bei {schnitt} s "
        f"Lesezeit statt {budget_sekunden} s. Fasse dich spürbar kürzer — "
        "vor allem bei den Punkten ab Position 2 und im Themen-Abschnitt.\n"
    )
