"""Lesezeit-Budget durchsetzen: Die Ausgabe wird auf ≤ 90 s gekürzt.

Bisher war das Budget nur eine Warnung (24.11.: 135 s, 25.11.: 120 s). Jetzt
kürzt ``kuerze_auf_budget`` nach der Synthese stufenweise, bis die geschätzte
Lesezeit passt — vom Entbehrlichsten zum Wichtigsten:

1. „Geprüft, nicht aufgenommen" auf 2 Einträge, „Deine Themen" auf 1 Zeile
2. „Was kommt" bei den Punkten ab 2 streichen
3. Punkte ab 2: „Was ist neu" und „Warum es zählt" auf je einen Satz
4. Punkt 1: „Was kommt" streichen, „Was ist neu" auf zwei, dann einen Satz
5. „Geprüft, nicht aufgenommen" und „Deine Themen" ganz streichen
6. Letzter Ausweg: hinterste Punkte streichen, aber nie unter 3 Punkte

Nie angetastet werden: Überschriften, Quellenklammer und Quell-Link jedes
verbleibenden Punkts und Punkt 1 (der Aufmacher) als Ganzes.
"""
from __future__ import annotations

import re

from . import i18n, qualitaet

_LABELS = {
    "de": {"neu": "**Was ist neu:**", "warum": "**Warum es zählt:**", "kommt": "**Was kommt:**"},
    "en": {"neu": "**What's new:**", "warum": "**Why it matters:**", "kommt": "**What's next:**"},
}
# Abkürzungen, nach deren Punkt kein Satz endet („340 Mio. Euro", „z. B. die").
_ABK = {"mio", "mrd", "bzw", "ca", "dr", "nr", "inkl", "abs", "st", "vgl", "z", "b", "u", "a",
        "etc", "prof", "mag", "ing", "tsd", "jän", "feb", "okt", "nov", "dez", "mr", "mrs"}
MIN_PUNKTE = 3


def erster_satz(text: str, saetze: int = 1) -> str:
    """Die ersten ``saetze`` Sätze — robust gegen „Mio. Euro" und „20. November"."""
    ende = 0
    gezaehlt = 0
    for m in re.finditer(r"[.!?](?=\s+[A-ZÄÖÜ„\"(]|\s*$)", text):
        davor = re.search(r"([\wÄÖÜäöüß]+)$", text[:m.start()])
        wort = davor.group(1) if davor else ""
        if wort.lower() in _ABK or wort.isdigit():
            continue
        gezaehlt += 1
        ende = m.end()
        if gezaehlt >= saetze:
            return text[:ende]
    return text


def _schwanz(text: str) -> tuple[str, str]:
    """Trennt Quellenklammer + Link am Zeilenende ab (bleiben immer stehen)."""
    m = qualitaet._QUELLE_SCHWANZ_RE.search(text)
    schwanz = m.group(1) if m else ""
    return (text[: len(text) - len(schwanz)] if schwanz else text), schwanz


def _kuerze_zeile(zeile: str, label: str, saetze: int) -> str:
    if not zeile.startswith(label):
        return zeile
    kern, schwanz = _schwanz(zeile[len(label):])
    neu = erster_satz(kern.strip(), saetze)
    return f"{label} {neu}{schwanz}" if neu else zeile


def _bloecke(lines: list[str]) -> list[tuple[int, int]]:
    starts = [i for i, l in enumerate(lines) if re.match(r"## \d", l)]
    return [(s, next((j for j in range(s + 1, len(lines))
                      if lines[j].startswith("## ") or lines[j].startswith("---")), len(lines)))
            for s in starts]


def _abschnitt(lines: list[str], marker: str) -> tuple[int, int] | None:
    s = next((i for i, l in enumerate(lines) if l.startswith("## ") and marker in l), None)
    if s is None:
        return None
    e = next((j for j in range(s + 1, len(lines))
              if lines[j].startswith("## ") or lines[j].startswith("---")), len(lines))
    return s, e


def _kappe_abschnitt(md: str, marker: str, max_zeilen: int) -> str:
    lines = md.splitlines()
    ab = _abschnitt(lines, marker)
    if ab is None:
        return md
    s, e = ab
    bullets = [i for i in range(s + 1, e) if lines[i].lstrip().startswith(("-", "*", "•"))]
    if len(bullets) <= max_zeilen:
        return md
    if max_zeilen == 0:
        neu = lines[:s] + lines[e:]
    else:
        weg = set(bullets[max_zeilen:])
        neu = [l for i, l in enumerate(lines) if i not in weg]
    return "\n".join(neu)


def _je_punkt(md: str, fn, ab_punkt: int = 2, bis_punkt: int | None = None) -> str:
    lines = md.splitlines()
    for n, (s, e) in enumerate(_bloecke(lines), 1):
        if n < ab_punkt or (bis_punkt and n > bis_punkt):
            continue
        for i in range(s + 1, e):
            lines[i] = fn(lines[i])
    return "\n".join(lines)


def _streiche_label(md: str, label: str, ab_punkt: int, bis_punkt: int | None = None) -> str:
    lines = md.splitlines()
    weg = set()
    for n, (s, e) in enumerate(_bloecke(lines), 1):
        if n < ab_punkt or (bis_punkt and n > bis_punkt):
            continue
        for i in range(s + 1, e):
            if lines[i].startswith(label):
                kern, schwanz = _schwanz(lines[i][len(label):])
                if schwanz.strip():  # Quelle/Link hing am Ausblick → als eigene Zeile retten
                    lines[i] = schwanz.strip()
                else:
                    weg.add(i)
    return "\n".join(l for i, l in enumerate(lines) if i not in weg)


def _streiche_letzten_punkt(md: str) -> str:
    lines = md.splitlines()
    bloecke = _bloecke(lines)
    if len(bloecke) <= MIN_PUNKTE:
        return md
    s, e = bloecke[-1]
    while e > s and e < len(lines) and not lines[e - 1].strip():
        e -= 1
    neu = lines[:s] + lines[e:]
    # doppelte Leerzeilen an der Nahtstelle vermeiden
    text = "\n".join(neu)
    return re.sub(r"\n{3,}", "\n\n", text)


def kuerze_auf_budget(markdown: str, budget: int, wps: float,
                      lang: str = "de") -> tuple[str, list[str]]:
    """Kürzt stufenweise, bis die Lesezeit ≤ budget ist. → (Markdown, Schritte)."""
    lab = _LABELS.get(lang, _LABELS["de"])
    pruef = i18n.t(lang, "nicht_aufgenommen_marker")
    themen = i18n.t(lang, "tracker_heading")
    stufen = [
        ("„Geprüft, nicht aufgenommen“ auf 2", lambda m: _kappe_abschnitt(m, pruef, 2)),
        ("Themen-Abschnitt auf 1 Zeile", lambda m: _kappe_abschnitt(m, themen, 1)),
        ("„Was kommt“ ab Punkt 2 gestrichen", lambda m: _streiche_label(m, lab["kommt"], 2)),
        ("„Was ist neu“ ab Punkt 2 auf 1 Satz",
         lambda m: _je_punkt(m, lambda z: _kuerze_zeile(z, lab["neu"], 1))),
        ("„Warum es zählt“ ab Punkt 2 auf 1 Satz",
         lambda m: _je_punkt(m, lambda z: _kuerze_zeile(z, lab["warum"], 1))),
        ("„Was kommt“ in Punkt 1 gestrichen", lambda m: _streiche_label(m, lab["kommt"], 1, 1)),
        ("„Was ist neu“ in Punkt 1 auf 2 Sätze",
         lambda m: _je_punkt(m, lambda z: _kuerze_zeile(z, lab["neu"], 2), 1, 1)),
        ("„Geprüft, nicht aufgenommen“ gestrichen", lambda m: _kappe_abschnitt(m, pruef, 0)),
        ("Themen-Abschnitt gestrichen", lambda m: _kappe_abschnitt(m, themen, 0)),
        ("„Was ist neu“ in Punkt 1 auf 1 Satz",
         lambda m: _je_punkt(m, lambda z: _kuerze_zeile(z, lab["neu"], 1), 1, 1)),
    ]
    schritte: list[str] = []
    md = markdown
    for name, fn in stufen:
        if qualitaet.lesezeit_sekunden(md, wps) <= budget:
            break
        neu = fn(md)
        if neu.rstrip("\n") != md.rstrip("\n"):
            md = neu
            schritte.append(name)
    while qualitaet.lesezeit_sekunden(md, wps) > budget:
        neu = _streiche_letzten_punkt(md)
        if neu == md:
            break
        md = neu
        schritte.append("letzten Punkt gestrichen")
    if schritte:
        md, _ = qualitaet.synchronisiere_heute_wichtig(md)
        if markdown.endswith("\n") and not md.endswith("\n"):
            md += "\n"
    return md, schritte
