"""Zeittreue: relative Tagesangaben müssen zum genannten Datum passen.

Vorfall 27.11.2026 (Freitag), Punkt „Spritpreisbremse": Text und Reifegrad
sagen „Ab 1. Dezember" / „Gilt ab 1.12", „Warum es zählt" sagt „ab Montag" —
der 1.12.2026 ist ein Dienstag. Das Modell hat den Wochentag selbst
ausgerechnet, und falsch.

Regel (deterministisch, je Punkt): Steht im Punkt ein explizites Datum in der
kommenden Woche, muss eine zukunftsbezogene Wochentags-/Morgen-Angabe („ab Montag", „bis Freitag",
„nächsten Dienstag", „ab morgen", „übermorgen") auf eines dieser Daten fallen
(gerechnet vom Ausgabedatum). Sonst wird sie durch das Datum ersetzt — bei
genau einem Datum —, bei mehreren Daten wird die Angabe gestrichen. Ohne
explizites Datum ist nichts prüfbar; dann bleibt der Text, wie er ist.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Jänner", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
          "September", "Oktober", "November", "Dezember"]
_MONAT_NR = {m.lower(): i + 1 for i, m in enumerate(MONATE)} | {"januar": 1}

_DATUM_TEXT_RE = re.compile(
    r"\b(\d{1,2})\.\s*(" + "|".join(list(_MONAT_NR)) + r")\b(?:\s+(\d{4}))?", re.IGNORECASE)
# Zahlen-Datum nur nach Zeit-Präposition („ab 1.12", „Gilt ab 1.12.") — sonst
# wäre „3.5 Prozent" der 3. Mai.
_DATUM_ZAHL_RE = re.compile(
    r"\b(?:ab|am|bis|vom|zum|per|seit)\s+(\d{1,2})\.(\d{1,2})\.?(\d{2,4})?(?![\d,])", re.IGNORECASE)
_WT = "|".join(WOCHENTAGE)
# Nur eindeutig zukunftsbezogene Angaben — „am Montag" kann Vergangenheit sein.
_RELATIV_RE = re.compile(
    rf"\b(?P<phrase>(?P<prep>ab|bis)\s+(?:(?:kommenden|nächsten|diesem|diesen)\s+)?(?P<wt>{_WT})"
    rf"|(?:kommenden|nächsten)\s+(?P<wt2>{_WT})"
    rf"|(?P<prep3>ab|bis)\s+(?P<morgen>übermorgen|morgen)"
    rf"|(?<!heute )(?P<morgen2>übermorgen))\b"
)


def _jahr(tag: int, monat: int, jahr: str | None, heute: date) -> date | None:
    try:
        if jahr:
            j = int(jahr)
            return date(j + 2000 if j < 100 else j, monat, tag)
        d = date(heute.year, monat, tag)
        return d if d >= heute - timedelta(days=7) else date(heute.year + 1, monat, tag)
    except ValueError:
        return None


def daten(text: str, heute: date) -> list[date]:
    """Explizite Daten im Text (ohne Duplikate, in Reihenfolge)."""
    gefunden: list[date] = []
    for m in _DATUM_TEXT_RE.finditer(text):
        d = _jahr(int(m.group(1)), _MONAT_NR[m.group(2).lower()], m.group(3), heute)
        if d and d not in gefunden:
            gefunden.append(d)
    for m in _DATUM_ZAHL_RE.finditer(text):
        tag, monat = int(m.group(1)), int(m.group(2))
        if 1 <= monat <= 12:
            d = _jahr(tag, monat, m.group(3), heute)
            if d and d not in gefunden:
                gefunden.append(d)
    return gefunden


def datum_text(d: date) -> str:
    return f"{d.day}. {MONATE[d.month - 1]}"


def _ziele(m: re.Match, heute: date) -> list[date]:
    """Auf welche Tage die relative Angabe fallen kann — „ab Montag" an einem
    Montag kann heute oder in einer Woche meinen (3.8.: U4 „ab Montag")."""
    morgen = m.group("morgen") or m.group("morgen2")
    if morgen:
        return [heute + timedelta(days=2 if morgen == "übermorgen" else 1)]
    wt = WOCHENTAGE.index(m.group("wt") or m.group("wt2"))
    delta = (wt - heute.weekday()) % 7
    return [heute, heute + timedelta(days=7)] if delta == 0 else [heute + timedelta(days=delta)]


def pruefe_wochentage(markdown: str, heute: date) -> tuple[str, list[str]]:
    """Korrigiert unpassende Wochentags-/Morgen-Angaben je Punkt. → (md, Korrekturen)."""
    lines = markdown.splitlines()
    korrekturen: list[str] = []
    starts = [i for i, l in enumerate(lines) if re.match(r"## \d", l)]
    for n, s in enumerate(starts, 1):
        e = next((j for j in range(s + 1, len(lines))
                  if lines[j].startswith("## ") or lines[j].startswith("---")), len(lines))
        block = "\n".join(lines[s:e])
        # Nur Daten der kommenden Woche: Ein Wochentag zeigt nie weiter voraus;
        # ein fernes Datum („Gilt ab 01.01.2027") meint etwas anderes (7.10.: „bis
        # Donnerstag" war eine Einreichfrist).
        termine = [d for d in daten(block, heute) if heute <= d <= heute + timedelta(days=7)]
        if not termine:
            continue
        for i in range(s, e):
            def ersetze(m: re.Match) -> str:
                ziele = _ziele(m, heute)
                if any(z in termine for z in ziele):
                    return m.group(0)
                ziel = ziele[-1] if len(ziele) > 1 else ziele[0]
                wt = WOCHENTAGE[ziel.weekday()]
                if len(termine) == 1:
                    prep = m.group("prep") or m.group("prep3") or "am"
                    neu = f"{prep} {datum_text(termine[0])}"
                    if m.group(0)[0].isupper():
                        neu = neu[0].upper() + neu[1:]
                else:
                    neu = ""
                korrekturen.append(
                    f"Punkt {n}: „{m.group(0)}“ (= {wt}, {ziel:%d.%m.}) passt zu keinem Datum im "
                    f"Punkt ({', '.join(f'{d:%d.%m.}' for d in termine)}) → „{neu or '(gestrichen)'}“"
                )
                return neu
            neu = _RELATIV_RE.sub(ersetze, lines[i])
            if neu != lines[i]:
                lines[i] = re.sub(r"\s{2,}", " ", neu).replace(" ,", ",").replace(" .", ".")
    if not korrekturen:
        return markdown, []
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else ""), korrekturen
