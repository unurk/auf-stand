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


# ── Zeichen-Hygiene ──────────────────────────────────────────────────────────
# Das Modell liefert vereinzelt Glyphen, die in einem deutschen/englischen
# Lagebild nie legitim sind — beobachtet: „⣣" statt der Nummern-Keycap in
# „Heute wichtig". Gefiltert werden nur Blöcke, die hier nichts verloren haben;
# Emojis, Keycaps (Ziffer + U+FE0F + U+20E3), ZWJ-Sequenzen, Umlaute und
# typografische Zeichen bleiben unangetastet.
_FREMDZEICHEN_KLASSE = (
    "["
    "\u2800-\u28ff"          # Braille
    "\ue000-\uf8ff"          # Private Use Area
    "\U000f0000-\U0010ffff"  # Supplementary Private Use
    "\ufffd"                 # Replacement Character (kaputtes Encoding)
    "\u3040-\u30ff"          # Hiragana/Katakana
    "\u3400-\u4dbf"          # CJK Extension A
    "\u4e00-\u9fff"          # CJK Unified Ideographs
    "\uac00-\ud7af"          # Hangul
    "\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f"  # Steuerzeichen (außer \\t \\n \\r)
    "]"
)
_FREMDZEICHEN_RE = re.compile(_FREMDZEICHEN_KLASSE + "+")
# Am Wort-/Zeilen-/Tag-Anfang: das folgende Leerzeichen mit entfernen.
_FREMDZEICHEN_ANFANG_RE = re.compile(
    r"(?<![^\s>])" + _FREMDZEICHEN_KLASSE + "+[ \u00a0]*"
)


def bereinige_zeichen(text: str) -> str:
    """Entfernt Fremd-/Steuerzeichen aus Modell-Output (idempotent).

    Steht das Zeichen am Wort-/Zeilenanfang (z. B. „⣣ EU-Staaten …"), fällt das
    nachfolgende Leerzeichen mit weg; Einrückungen anderer Zeilen bleiben.
    """
    if not text:
        return text
    return _FREMDZEICHEN_RE.sub("", _FREMDZEICHEN_ANFANG_RE.sub("", text))


# ── Reifegrad nur, wo es eine Regelung gibt ─────────────────────────────────
# „Entwurf" / „Gilt ab …" beantwortet „muss ich mich kümmern?" — das ergibt nur
# bei Politik, Recht und Regelungen Sinn. Bei einem Unfall oder Angriff wirkt
# ein „Beschlossen"-Badge absurd. Der Prompt regelt das; dieses Gate fängt den
# Rest deterministisch ab.
_REIFEGRAD_ZEILE_RE = re.compile(
    r"^\*\*(?:Reifegrad|Status):\*\*\s*(?P<wert>.*)$", re.MULTILINE
)
_REIFEGRAD_GUELTIG_RE = re.compile(
    r"gerücht|geruecht|entwurf|beschlossen|gilt ab|in kraft|"
    r"rumou?red|draft|proposed|decided|passed|effective|in force",
    re.IGNORECASE,
)
_EREIGNIS_RE = re.compile(
    r"\b(?:unfall|unfälle|unglück|absturz|abgestürzt|anschlag|anschläge|angriff|angriffe|"
    r"attacke|attentat|explosion|brand|feuer|erdbeben|unwetter|hochwasser|"
    r"überschwemmung|lawine|tote|toten|todesopfer|verletzt\w*|getötet|ermordet|mord|"
    r"schüsse|schießerei|messer\w*|geisel\w*|entführ\w*|festgenommen|festnahme|"
    r"razzia|drohnenangriff\w*|raketenangriff\w*|luftangriff\w*|"
    r"accident|crash|attack\w*|shooting|explosion|fire|earthquake|flood\w*|"
    r"killed|injured|dead|hostage\w*|arrested)\b",
    re.IGNORECASE,
)
_REGELUNG_RE = re.compile(
    r"(?:gesetz|verordnung|novelle|richtlinie|regelung|reform|beschluss|beschließt|"
    r"beschlossen|nationalrat|bundesrat|parlament|landtag|ministerrat|"
    r"begutachtung|regierungsvorlage|in kraft|gilt ab|verfassung|vfgh|vwgh|ogh|eugh|"
    r"höchstgericht|urteil|steuer|abgabe|gebühr|förderung|pension|budget|zoll|zölle|"
    r"sanktion|leitzins|kollektivvertrag|mindestlohn|"
    r"\blaw\b|legislation|regulation|bill\b|congress|senate|supreme court|ruling|"
    r"tariff|\btax|interest rate|sanction)",
    re.IGNORECASE,
)
_REGELUNGS_RESSORTS = ("🏛", "⚖")


def reifegrad_passt(wert: str, punkt_text: str, kopf: str = "") -> bool:
    """True, wenn ein Reifegrad-Badge zu diesem Punkt passt.

    - Wert außerhalb des Vokabulars (z. B. „Ereignis", „entfällt") → nein.
    - Mehr Ereignis- als Regelungs-Signale im Punkt (Unfall, Angriff, Tote …
      vs. Gesetz, Beschluss, Nationalrat …) → nein. Politik-/Recht-Ressort
      (🏛/⚖️) im Kopf zählt als zusätzliches Regelungs-Signal.
    """
    if not _REIFEGRAD_GUELTIG_RE.search(wert or ""):
        return False
    ereignis = len(_EREIGNIS_RE.findall(punkt_text))
    regelung = len(_REGELUNG_RE.findall(punkt_text)) + (
        1 if any(e in kopf for e in _REGELUNGS_RESSORTS) else 0
    )
    return not (ereignis and ereignis >= regelung)


def entferne_reifegrad_bei_ereignissen(markdown: str) -> tuple[str, int]:
    """Entfernt unpassende Reifegrad-Zeilen je Punkt (## <Ziffer>). → (md, anzahl)"""
    teile = re.split(r"(?m)^(?=## |---)", markdown)
    entfernt = 0
    neu: list[str] = []
    for teil in teile:
        m = _REIFEGRAD_ZEILE_RE.search(teil)
        if not (re.match(r"## \d", teil) and m):
            neu.append(teil)
            continue
        ohne = teil[: m.start()] + teil[m.end():]
        kopf = teil.split("\n", 1)[0]
        if not reifegrad_passt(m.group("wert").strip(), ohne, kopf):
            teil = re.sub(r"\n?" + re.escape(m.group(0)), "", teil, count=1)
            entfernt += 1
        neu.append(teil)
    return "".join(neu), entfernt


# ── „Gilt ab" nur mit echtem Datum ───────────────────────────────────────────
# Im Prompt steht als Format „Gilt ab TT.MM." — das Modell hat das am 17.11.
# wörtlich übernommen („Gilt ab TT.MM" als Badge). Ein „Gilt ab" ohne Datum
# sagt der Leserin nichts und sieht kaputt aus: Es fällt auf „Beschlossen"
# zurück (der Beschluss ist ja offenbar gefallen, nur das Datum fehlt).
_GILT_AB_RE = re.compile(r"^\s*(?:gilt ab|effective)\b", re.IGNORECASE)
_MONATE = (
    r"j[äa]n(?:ner|uar)?|feb(?:ruar)?|märz|maerz|mär|apr(?:il)?|mai|jun[i]?|jul[i]?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|okt(?:ober)?|nov(?:ember)?|dez(?:ember)?|"
    r"january|february|march|mar|april|may|june|july|august|september|"
    r"oct(?:ober)?|november|dec(?:ember)?"
)
_DATUM_RE = re.compile(
    r"\b\d{1,2}\.\s?\d{1,2}\.(?:\s?\d{2,4}\b)?"            # 17.11.  1.1.2027
    r"|\b(?:0?[1-9]|[12]\d|3[01])\.\s?(?:0?[1-9]|1[0-2])\b"  # 17.11 (Badge ohne Punkt)
    r"|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"                   # 11/17  1/1/2027
    r"|\b\d{4}-\d{2}-\d{2}\b"                              # 2027-01-01
    rf"|\b\d{{1,2}}\.?\s+(?:{_MONATE})\b\.?"                # 1. Jänner 2027, 17 Nov
    rf"|\b(?:{_MONATE})\.?\s+\d{{1,2}}\b"                   # November 17, Jan. 1
    rf"|\b(?:{_MONATE})\.?\s+\d{{4}}\b",                     # Jänner 2027
    re.IGNORECASE,
)


def hat_echtes_datum(text: str) -> bool:
    """True, wenn der Text ein konkretes Datum enthält (nicht „TT.MM"/„MM/DD")."""
    return bool(_DATUM_RE.search(text or ""))


def normalisiere_reifegrad(wert: str, lang: str = "de") -> str:
    """„Gilt ab"/„Effective" ohne echtes Datum → „Beschlossen"/„Decided".

    Alle anderen Werte (auch „Gilt ab 17.11.") bleiben unverändert.
    """
    if _GILT_AB_RE.match(wert or "") and not hat_echtes_datum(wert):
        return "Decided" if lang == "en" else "Beschlossen"
    return wert


def korrigiere_reifegrad_platzhalter(markdown: str, lang: str = "de") -> tuple[str, int]:
    """Wendet normalisiere_reifegrad auf alle Reifegrad-/Status-Zeilen an. → (md, anzahl)"""
    anzahl = 0

    def _ersetze(m: re.Match) -> str:
        nonlocal anzahl
        wert = m.group("wert").strip()
        neu = normalisiere_reifegrad(wert, lang)
        if neu == wert:
            return m.group(0)
        anzahl += 1
        return m.group(0).replace(m.group("wert"), neu, 1)

    return _REIFEGRAD_ZEILE_RE.sub(_ersetze, markdown), anzahl
