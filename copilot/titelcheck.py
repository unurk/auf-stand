"""Titel-Faktencheck: Zahlen in Titeln müssen im Text des Punkts stehen.

Vorfall 25.11.2026 (Morgen): Titel „A1 investiert 500 Millionen, streicht aber
Personal" — im Punkt stand nur „bis 2030 insgesamt 300 Millionen Euro
einsparen". Die 500 Mio. standen zwar in der Quell-Schlagzeile („A1 baut um:
500 Millionen Euro für die Zukunft …"), aber nicht im Text: Die Leserin sieht
Titel und Text, und die widersprachen sich.

Regel (deterministisch, nach der Synthese):
- Punkt-Titel: Jede Zahl muss im Text des Punkts vorkommen (Ziffern oder
  Zahlwort; Namen wie „COP31"/„A1" sind keine Zahlen). Sonst wird der Titel
  korrigiert — durch die Schlagzeile der Quell-Meldung, wenn deren Zahlen im
  Text stehen, ansonsten wird die ungedeckte Zahl samt Einheit gestrichen.
- H1: Jede Zahl muss in einem Punkt vorkommen, sonst wird die H1 zum
  (geprüften) Titel von Punkt 1.
- „Heute wichtig" wird danach aus den Titeln neu gebaut (main._pruefe_titel).
"""
from __future__ import annotations

import re

# Ziffern direkt an Buchstaben („COP31", „A1", „5G", „G20") sind Namen, keine Zahlen.
_ZAHL_RE = re.compile(r"(?<![\wÄÖÜäöüß])\d+(?:[.,]\d+)*(?![A-Za-zÄÖÜäöüß])")
# Zahlwörter im Text decken Ziffern im Titel („knapp zwölf Milliarden" ↔ „12-Milliarden").
_ZAHLWOERTER = {
    "zwei": "2", "drei": "3", "vier": "4", "fünf": "5", "sechs": "6", "sieben": "7",
    "acht": "8", "neun": "9", "zehn": "10", "elf": "11", "zwölf": "12", "zwanzig": "20",
    "dreißig": "30", "vierzig": "40", "fünfzig": "50", "hundert": "100", "tausend": "1000",
}
_EINHEIT = (r"(?:\s*(?:Mio\.?|Millionen|Mrd\.?|Milliarden|Tsd\.?|Tausend|Euro|EUR|€|"
            r"Dollar|\$|Prozent|%|Stellen|Jobs|Mal))*")
_VORSATZ = r"(?:(?:rund|fast|über|knapp|bis zu|mehr als|weitere|zusätzlich)\s+)?"


def zahlen(text: str, zahlwoerter: bool = True) -> set[str]:
    """Normierte Zahlen: „1.000" = „1000", „4,5" bleibt „4,5", ohne führende Nullen.

    Mit ``zahlwoerter`` zählen auch „zwölf" usw. — nur für die deckende Seite
    (Text, Material); im Titel prüfen wir Ziffern.
    """
    werte = set()
    for z in _ZAHL_RE.findall(text or ""):
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", z):
            z = z.replace(".", "")
        z = z.rstrip(".,")
        werte.add(z.lstrip("0") or "0")
    for wort in re.findall(r"[a-zäöüß]+", (text or "").lower()) if zahlwoerter else []:
        if wort in _ZAHLWOERTER:
            werte.add(_ZAHLWOERTER[wort])
    return werte


def _ohne_links(text: str) -> str:
    return re.sub(r"\]\([^)]*\)", "]", text)


def _punkte(lines: list[str]) -> list[tuple[int, int]]:
    """(Start, Ende) je nummeriertem Punkt in Zeilen-Indizes."""
    starts = [i for i, l in enumerate(lines) if re.match(r"## \d", l)]
    result = []
    for s in starts:
        e = next((j for j in range(s + 1, len(lines))
                  if lines[j].startswith("## ") or lines[j].startswith("---")), len(lines))
        result.append((s, e))
    return result


def _quelle(block: str, articles: list):
    links = re.findall(r"\]\(([^)]+)\)", block)
    for a in articles or []:
        if getattr(a, "link", "") and a.link in links:
            return a
    return None


def _titel_teile(zeile: str) -> tuple[str, str]:
    """„## 1️⃣ 📱 Titel" → („## 1️⃣ 📱 ", „Titel")."""
    m = re.match(r"^## \d️?⃣?\s*[^\wÄÖÜäöüß„\"'(«»]*", zeile)
    return m.group(0), zeile[m.end():]


def streiche_zahlen(titel: str, erlaubt: set[str]) -> str:
    """Streicht ungedeckte Zahlen samt Vorsatz/Einheit und räumt Satzzeichen auf."""
    def ersetze(m: re.Match) -> str:
        return m.group(0) if zahlen(m.group("z"), False) <= erlaubt else ""
    # „12-Milliarden-Schuldenberg" → „Milliarden-Schuldenberg"
    neu = re.sub(r"(?<![\wÄÖÜäöüß])(?P<z>\d+(?:[.,]\d+)*)-(?=[A-Za-zÄÖÜäöüß])",
                 lambda m: m.group(0) if zahlen(m.group("z"), False) <= erlaubt else "", titel)
    neu = re.sub(rf"(?<![A-Za-zÄÖÜäöüß]){_VORSATZ}(?P<z>\d+(?:[.,]\d+)*)(?![A-Za-zÄÖÜäöüß-]){_EINHEIT}",
                 ersetze, neu)
    # Stand die Zahl am Ende („Frist kostet 18.632 Euro"), bliebe ein Verb
    # ohne Objekt stehen — dann das nachgestellte kleingeschriebene Wort mit weg.
    if re.search(rf"{_VORSATZ}\d+(?:[.,]\d+)*{_EINHEIT}\s*$", titel) and neu.strip() != titel.strip():
        neu = re.sub(r"\s+[a-zäöüß]+\s*$", "", neu.rstrip())
    neu = re.sub(r"\s+([,;:—–-])", r"\1", neu)
    neu = re.sub(r"([,;:])(?=\S)", r"\1 ", neu)
    neu = re.sub(r"\s{2,}", " ", neu).strip(" ,;:—–-")
    return neu


def pruefe_titel(markdown: str, articles: list) -> tuple[str, list[str]]:
    """Prüft Punkt-Titel und H1. → (Markdown, Liste der Korrekturen fürs Log)."""
    lines = markdown.splitlines()
    korrekturen: list[str] = []
    alle_erlaubt: set[str] = set()
    punkt1_titel = None
    for n, (s, e) in enumerate(_punkte(lines)):
        block = "\n".join(lines[s + 1:e])
        quelle = _quelle(block, articles)
        erlaubt = zahlen(_ohne_links(block))
        praefix, titel = _titel_teile(lines[s])
        ungedeckt = zahlen(titel, False) - erlaubt
        if ungedeckt:
            kandidat = quelle.title.strip() if quelle else ""
            if kandidat and zahlen(kandidat, False) <= erlaubt:
                neu = kandidat
            else:
                neu = streiche_zahlen(titel, erlaubt)
            if neu and neu != titel:
                lines[s] = praefix + neu
                korrekturen.append(
                    f"Punkt {n + 1}: Zahl(en) {', '.join(sorted(ungedeckt))} nicht im Text — "
                    f"„{titel}“ → „{neu}“"
                )
                titel = neu
        alle_erlaubt |= erlaubt | zahlen(titel, False)
        if punkt1_titel is None:
            punkt1_titel = titel
    h1 = next((i for i, l in enumerate(lines) if l.startswith("# ")), None)
    if h1 is not None and punkt1_titel:
        prefix = re.match(r"^# [^\wÄÖÜäöüß„\"']*", lines[h1]).group(0)
        kopf = lines[h1][len(prefix):]
        ungedeckt = zahlen(kopf, False) - alle_erlaubt
        if ungedeckt:
            lines[h1] = prefix + punkt1_titel
            korrekturen.append(
                f"H1: Zahl(en) {', '.join(sorted(ungedeckt))} nicht im Text — "
                f"„{kopf}“ → „{punkt1_titel}“"
            )
    if not korrekturen:
        return markdown, []
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else ""), korrekturen
