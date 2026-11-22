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


# ── „Heute wichtig" spiegelt die Punkte ──────────────────────────────────────
# Liste und Punkte entstehen im selben Modell-Aufruf, aber nichts zwingt das
# Modell, beide konsistent zu halten. Darum wird die Liste nach der Synthese
# deterministisch aus den Punkt-Überschriften neu gebaut: gleiche Anzahl,
# gleiche Reihenfolge, gleiches Thema.
_HEUTE_LABELS = ("**Heute wichtig:**", "**Today's headlines:**")
_KEYCAP_PREFIX_RE = re.compile(r"^\d️?⃣\s*")


def punkt_titel(markdown: str) -> list[str]:
    """Überschriften der nummerierten Punkte (ohne Nummer-Keycap und Ressort-Emoji)."""
    titel = []
    for zeile in markdown.splitlines():
        if not re.match(r"## \d", zeile):
            continue
        t = _KEYCAP_PREFIX_RE.sub("", zeile[3:].strip())
        t = re.sub(r"^[^\w„\"'(«»]+", "", t).strip()  # Ressort-Emoji(s) am Anfang
        if t:
            titel.append(t)
    return titel


def synchronisiere_heute_wichtig(markdown: str) -> tuple[str, bool]:
    """Baut „Heute wichtig" aus den Punkt-Überschriften neu. → (md, geändert)

    Ohne nummerierte Punkte (Ruhige Lage) bleibt der Block unangetastet.
    """
    titel = punkt_titel(markdown)
    if not titel:
        return markdown, False
    lines = markdown.splitlines()
    start = next((i for i, l in enumerate(lines) if l.strip() in _HEUTE_LABELS), None)
    if start is None:
        return markdown, False
    ende = start + 1
    while ende < len(lines) and not (
        lines[ende].startswith("---") or lines[ende].startswith("## ")
    ):
        ende += 1
    # Leerzeilen vor dem Trenner erhalten
    inhalt_ende = ende
    while inhalt_ende > start + 1 and not lines[inhalt_ende - 1].strip():
        inhalt_ende -= 1
    neu_block = [f"{i}️⃣ {t}" for i, t in enumerate(titel, 1)]
    if lines[start + 1 : inhalt_ende] == neu_block:
        return markdown, False
    if inhalt_ende == ende:  # kein Abstand zum Trenner vorhanden → einen setzen
        neu_block.append("")
    neu = lines[: start + 1] + neu_block + lines[inhalt_ende:]
    return "\n".join(neu) + ("\n" if markdown.endswith("\n") else ""), True


# ── Sprache: durchgehend Deutsch ─────────────────────────────────────────────
# Beobachtet am 18.11.: „drohen store closures". Englische Einsprengsel werden
# erkannt (Wortliste + Endungs-Heuristik), bekannte Fälle direkt ersetzt; was
# übrig bleibt, lässt main.py einmal vom Modell korrigieren.
#
# Bewusst nur kleingeschriebene Treffer: Deutsche Nomen sind großgeschrieben,
# etablierte Lehnwörter („Deal", „Job") ebenso. Ein kleingeschriebenes
# „closures" oder „the" ist dagegen sicher Englisch. Wörter, die es auch im
# Deutschen gibt („will", „was", „die", „also"), stehen nicht auf der Liste.
_ENGLISCHE_WOERTER = frozenset("""
the and of with for which would could should been their they this that these those
from into about between however although because whereas despite amid without within
through against among its are were has have had not but is it be by or on at
store stores closure closures shutdown shutdowns layoff layoffs earnings outlook growth
rates tariff tariffs revenue revenues sales shares stake profit profits deficit inflation
spending workers worker strike strikes talks deadline lockdown headwinds
tailwinds update breaking market markets company companies government
""".split())
# Typisch englische Endungen bei kleingeschriebenen Wörtern (deutsche
# Kleinwörter enden so praktisch nie — Ausnahmen unten).
_ENGLISCHE_ENDUNG_RE = re.compile(r"\b[a-z]{3,}(?:ures|ings|tions|ments|ness|ships)\b")
_DEUTSCHE_AUSNAHMEN = frozenset({"allerdings", "neuerdings", "schlechterdings", "platterdings"})
# Bekannte Fälle mit eindeutiger Übersetzung: direkt ersetzen, kein Modell-Aufruf.
ANGLIZISMEN = {
    "store closures": "Geschäftsschließungen",
    "closures": "Schließungen",
    "layoffs": "Kündigungen",
    "earnings": "Quartalszahlen",
    "tariffs": "Zölle",
    "shutdown": "Stillstand",
    "deadline": "Frist",
    "headwinds": "Gegenwind",
}


def _pruefbarer_text(markdown: str) -> str:
    """Text ohne Links, URLs, Zitate und Quellenklammern — dort ist Englisch legitim."""
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", " ", markdown)          # Markdown-Links
    t = re.sub(r"https?://\S+", " ", t)
    t = re.sub(r"„[^“”\"]*[“”\"]|\"[^\"]*\"|“[^”]*”|»[^«]*«", " ", t)  # Zitate/Titel
    t = re.sub(r"\([^)]*·[^)]*\)", " ", t)                       # (Ressort · Bericht: …)
    return t


def finde_englisch(markdown: str) -> list[str]:
    """Englische Wörter im deutschen Fließtext (eindeutig, in Fundreihenfolge)."""
    text = _pruefbarer_text(markdown)
    treffer: list[str] = []
    for wort in re.findall(r"(?<![\w-])[a-z][a-z']*(?![\w-])", text):
        if wort in _ENGLISCHE_WOERTER and wort not in treffer:
            treffer.append(wort)
    for wort in _ENGLISCHE_ENDUNG_RE.findall(text):
        if wort not in _DEUTSCHE_AUSNAHMEN and wort not in treffer:
            treffer.append(wort)
    return treffer


def ersetze_anglizismen(markdown: str) -> tuple[str, int]:
    """Ersetzt bekannte englische Ausdrücke (nur kleingeschrieben, ganze Wörter)."""
    anzahl = 0
    for en, de in sorted(ANGLIZISMEN.items(), key=lambda kv: -len(kv[0])):
        markdown, n = re.subn(rf"(?<![\w-]){re.escape(en)}(?![\w-])", de, markdown)
        anzahl += n
    return markdown, anzahl


# ── Anrede: keine weiblichen Rollenbezeichnungen für den Leser ───────────────
# Beobachtet am 18.11.: „Für dich als Konsumentin". Der Leser ist ein Mann.
_ROLLE_WEIBLICH_RE = re.compile(
    r"\b(?P<vor>(?:dich|dir|du|Du|Dich|Dir)\s+als\s+)"
    r"(?P<stamm>[A-ZÄÖÜ][a-zäöüß]+?(?:er|ent|ant|ist|eur|är|ör|tor|ar))"
    r"(?P<suffix>in|:in|\*in|_in|In)\b"
)
_ROLLE_SONDERFAELLE = {"Kundin": "Kunde", "Beamtin": "Beamter", "Expertin": "Experte"}


def neutralisiere_anrede(markdown: str) -> tuple[str, int]:
    """„dich als Konsumentin/Konsument:in" → „dich als Konsument". → (md, anzahl)"""
    anzahl = 0

    def _sonder(m: re.Match) -> str:
        nonlocal anzahl
        anzahl += 1
        return m.group(1) + _ROLLE_SONDERFAELLE[m.group(2)]

    markdown = re.sub(
        r"\b((?:dich|dir|du|Du|Dich|Dir)\s+als\s+)(" + "|".join(_ROLLE_SONDERFAELLE) + r")\b",
        _sonder, markdown,
    )

    def _ersetze(m: re.Match) -> str:
        nonlocal anzahl
        anzahl += 1
        return m.group("vor") + m.group("stamm")

    return _ROLLE_WEIBLICH_RE.sub(_ersetze, markdown), anzahl


# ── Meta-Floskeln in „Warum es zählt" ────────────────────────────────────────
_META_FLOSKEL_RE = re.compile(
    r"\s*\b(?:Für dein(?:\s+\w+)?\s+Verständnis|For your(?:\s+\w+)?\s+understanding)\s*:\s*",
    re.IGNORECASE,
)


def entferne_meta_floskeln(markdown: str) -> tuple[str, int]:
    """Entfernt „Für dein politisches Verständnis:"-Einleitungen. → (md, anzahl)"""
    def _ersetze(m: re.Match) -> str:
        return " " if m.start() > 0 else ""

    neu, n = _META_FLOSKEL_RE.subn(_ersetze, markdown)
    return neu, n


# ── Überschrift: echte Schlagzeile statt Meta-Floskel ────────────────────────
# Beobachtet am 19.11.: H1 „Bereit?". Generische Titel (Begrüßungen, „Dein
# Lagebild", reine Datumszeilen) werden durch die Schlagzeile des Aufmachers
# ersetzt.
_META_PHRASEN_RE = re.compile(
    r"\b(?:bereit|ready|guten (?:morgen|tag|abend|nachmittag)|"
    r"good (?:morning|afternoon|evening)|dein(?:e)? lagebild|your briefing|the briefing|"
    r"lagebild|briefing|los geht'?s|here we go|hallo|hi|hello|"
    r"willkommen(?: zurück)?|welcome(?: back)?|ein neuer tag|a new day|"
    r"schön,? dass du (?:da bist|schaust|wieder da bist)|kurze pause|halbzeit|"
    r"fast geschafft|kurz innehalten|noch ein blick|mitten im tag|feierabend|"
    r"der tag,? kompakt|der abend gehört dir|was bleibt vom tag|was sich getan hat|"
    r"frisch informiert starten|hier ist er|kurz nachgeholt|kurz(?: noch)?|"
    r"das wichtigste(?: heute| des tages)?|today'?s update|update|überblick|"
    r"der überblick(?: zur mittagszeit)?|der nachmittag,? kompakt|da sind wir)\b",
    re.IGNORECASE,
)
_DATUMSZEILE_RE = re.compile(
    r"\b(?:montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|monday|tuesday|"
    r"wednesday|thursday|friday|saturday|sunday|"
    rf"{_MONATE}|"
    r"(?:morgen|mittags|nachmittags|abend)-ausgabe|ausgabe|edition|catch-up|"
    r"morning|midday|afternoon|evening|uhr)\b",
    re.IGNORECASE,
)


def ist_meta_ueberschrift(text: str) -> bool:
    """True, wenn die Überschrift keinen Inhalt trägt (Begrüßung, Datum, „Lagebild")."""
    rest = _META_PHRASEN_RE.sub(" ", text or "")
    rest = _DATUMSZEILE_RE.sub(" ", rest)
    return not re.search(r"[A-Za-zÄÖÜäöüß]{3,}", rest)


def korrigiere_h1(markdown: str, ersatz_ohne_punkte: str = "Ruhige Lage") -> tuple[str, bool]:
    """Ersetzt eine Meta-H1 durch die Schlagzeile des ersten Punktes. → (md, geändert)"""
    lines = markdown.splitlines()
    idx = next((i for i, l in enumerate(lines) if l.startswith("# ")), None)
    if idx is None:
        return markdown, False
    h1 = lines[idx][2:]
    prefix = re.match(r"^[^\wÄÖÜäöüß„\"']*", h1).group(0)  # Ausgaben-Emoji behalten
    if not ist_meta_ueberschrift(h1[len(prefix):]):
        return markdown, False
    titel = punkt_titel(markdown)
    lines[idx] = f"# {prefix}{titel[0] if titel else ersatz_ohne_punkte}"
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else ""), True


# ── Einheitliche Struktur: jeder Punkt hat „Was ist neu" und „Warum es zählt" ─
# Beobachtet am 19.11.: Punkt 4 („Medienförderung") war nur ein Fließtextsatz —
# der Prompt hatte für Punkte 4–5 „knappe Ein-Zeiler" verlangt.
_LABELS = {
    "de": ("**Was ist neu:**", "**Warum es zählt:**"),
    "en": ("**What's new:**", "**Why it matters:**"),
}
_LABEL_ZEILE_RE = re.compile(r"^\*\*[^*]{2,40}:\*\*")
_QUELLE_ENDE_RE = re.compile(
    r"\s*(?P<tail>(?:\([^()]*\)\s*)?(?:\[→[^\]]*\]\([^)]*\)\s*)?)$"
)


def _punkt_teile(markdown: str) -> list[str]:
    return re.split(r"(?m)^(?=## |---)", markdown)


def fehlende_struktur(markdown: str, lang: str = "de") -> list[int]:
    """1-basierte Nummern der Punkte, denen „Was ist neu" oder „Warum es zählt" fehlt."""
    neu, warum = _LABELS.get(lang, _LABELS["de"])
    fehlend, nr = [], 0
    for teil in _punkt_teile(markdown):
        if re.match(r"## \d", teil):
            nr += 1
            if neu not in teil or warum not in teil:
                fehlend.append(nr)
    return fehlend


def _teile_satz(satz: str, lang: str) -> tuple[str, str] | None:
    """Teilt einen einzelnen Satz in Änderung + Folge (an „und"/„;"/„—"), sonst None."""
    satz = satz.strip()
    ende = satz[-1] if satz[-1:] in ".!?" else "."
    kern = satz.rstrip(".!?")
    for trenner, anschluss in (("; ", ""), (" — ", ""), (" – ", ""),
                               (" und ", "Das " if lang == "de" else "This "),
                               (" and ", "This ")):
        pos = kern.rfind(trenner)
        if pos == -1:
            continue
        links, rechts = kern[:pos].strip(), kern[pos + len(trenner):].strip()
        if len(links.split()) >= 4 and len(rechts.split()) >= 3:
            rechts = anschluss + rechts if anschluss else rechts[:1].upper() + rechts[1:]
            return links + ".", rechts + ende
    return None


def repariere_struktur(markdown: str, lang: str = "de") -> tuple[str, int]:
    """Gliedert Fließtext-Punkte deterministisch in beide Teile. → (md, repariert)

    Nur der Fall „Punkt ohne beide Labels": mehrere Sätze → erster Satz ist die
    Änderung, der Rest die Folge; ein einzelner Satz wird an „und"/„;"/„—"
    geteilt. Quelle/Link am Ende bleiben am Ende. Nicht teilbares bleibt stehen
    (main.py versucht vorher eine Modell-Reparatur und warnt sonst).
    """
    neu_l, warum_l = _LABELS.get(lang, _LABELS["de"])
    repariert = 0
    teile = _punkt_teile(markdown)
    for i, teil in enumerate(teile):
        if not re.match(r"## \d", teil) or neu_l in teil or warum_l in teil:
            continue
        zeilen = teil.split("\n")
        kopf, rumpf = zeilen[0], zeilen[1:]
        fliess = [z for z in rumpf if z.strip() and not _LABEL_ZEILE_RE.match(z.strip())]
        if not fliess:
            continue
        text = " ".join(z.strip() for z in fliess)
        m = _QUELLE_ENDE_RE.search(text)
        tail = m.group("tail").strip() if m else ""
        text = text[: m.start()].strip() if m and tail else text
        saetze = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ„\"])", text)
        if len(saetze) >= 2:
            was, warum = saetze[0], " ".join(saetze[1:])
        else:
            geteilt = _teile_satz(text, lang)
            if not geteilt:
                continue
            was, warum = geteilt
        neu_rumpf, gesetzt = [], False
        for z in rumpf:
            if z.strip() and not _LABEL_ZEILE_RE.match(z.strip()):
                if not gesetzt:
                    neu_rumpf += [f"{neu_l} {was}", f"{warum_l} {warum}" + (f" {tail}" if tail else "")]
                    gesetzt = True
                continue
            neu_rumpf.append(z)
        teile[i] = "\n".join([kopf] + neu_rumpf)
        repariert += 1
    return "".join(teile), repariert


# ── „Deine Themen" ohne Doppelungen zu den Punkten ───────────────────────────
# Beobachtet am 19.11.: Die Airbnb-/Kurzzeitvermietungs-Meldung stand als Punkt 2
# UND als Themen-Zeile; die Nvidia-Zeile wiederholte den Anthropic-Punkt.
_STOPPWOERTER = frozenset("""
der die das den dem des ein eine einer eines einem einen und oder mit für von vom bei
auf aus nach seit über unter zum zur im in am an als auch nicht noch nur mehr wie was
wer wird werden wurde wurden hat haben hatte ist sind war sein seine seiner ihre ihr
dein deine deinem deinen deiner letzten letzter stand weiter neue neuen neuem neues
dass sich sie er es man vor bis durch gegen ohne um soll sollen will kann können
heute jetzt dabei damit davon dazu diese dieser dieses jedoch aber sowie bereits
since your last update the and of with for from that this into
""".split())


def _schluesselwoerter(text: str) -> set[str]:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    woerter = set()
    for wort in re.findall(r"[A-Za-zÄÖÜäöüß0-9][\wÄÖÜäöüß]*", text):
        w = wort.lower()
        if w in _STOPPWOERTER or len(w) < 4:
            continue
        if w.endswith("ungen"):
            w = w[:-2]
        else:
            for suf in ("en", "er", "es", "em", "e", "n", "s"):
                if w.endswith(suf) and len(w) - len(suf) >= 4:
                    w = w[: -len(suf)]
                    break
        woerter.add(w)
    return woerter


def ist_doppelung(zeile: str, punkt_texte: list[str]) -> bool:
    """True, wenn eine Themen-Zeile inhaltlich einen der Punkte wiederholt."""
    rumpf = re.sub(r"^\s*[-*•]\s*(?:\*\*[^*]+\*\*:?\s*)?", "", zeile)
    rumpf = re.sub(r"^(?:Seit deinem letzten Stand|Since your last update)\s*:?\s*", "",
                   rumpf, flags=re.IGNORECASE)
    z = _schluesselwoerter(rumpf)
    if not z:
        return False
    for text in punkt_texte:
        gemeinsam = z & _schluesselwoerter(text)
        if len(gemeinsam) >= 3 or (len(gemeinsam) >= 2 and len(gemeinsam) / len(z) >= 0.3):
            return True
    return False


def entferne_themen_doppelungen(markdown: str, heading: str = "Deine Themen") -> tuple[str, int]:
    """Streicht Themen-Zeilen, die schon als Punkt vorkommen; leerer Abschnitt fällt weg."""
    punkte = [t for t in _punkt_teile(markdown) if re.match(r"## \d", t)]
    if not punkte:
        return markdown, 0
    lines = markdown.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith("## ") and heading in l), None)
    if start is None:
        return markdown, 0
    ende = next((i for i in range(start + 1, len(lines))
                 if lines[i].startswith("## ") or lines[i].startswith("---")), len(lines))
    behalten, entfernt = [], 0
    for z in lines[start + 1 : ende]:
        if z.lstrip().startswith(("-", "*", "•")) and ist_doppelung(z, punkte):
            entfernt += 1
            continue
        behalten.append(z)
    if not entfernt:
        return markdown, 0
    if any(z.lstrip().startswith(("-", "*", "•")) for z in behalten):
        neu = lines[: start + 1] + behalten + lines[ende:]
    else:
        neu = lines[:start] + lines[ende:]
    return "\n".join(neu) + ("\n" if markdown.endswith("\n") else ""), entfernt


# ── Rechtschreibung: Korrekturdurchgang für Titel und „Warum es zählt" ───────
# Beobachtet am 22.11.: „hötere Belastungen", „Auslandsdelivrung", „könnte Kosten
# … weitergereicht werden", „Klimakonferenz drohen zu scheitern". Korrigiert
# werden nur die sichtbarsten Zeilen (H1, Punkt-Titel, „Warum es zählt") — und
# eine Korrektur gilt nur, wenn sie klein ist und keine Zahl verändert.
_WARUM_LABELS = ("**Warum es zählt:**", "**Why it matters:**")
_QUELLE_SCHWANZ_RE = re.compile(r"(\s*(?:\([^()]*\)\.?\s*)?(?:\[→[^\]]*\]\([^)]*\)\s*)?)$")
MIN_AEHNLICHKEIT = 0.8


def korrektur_zeilen(markdown: str) -> list[tuple[int, str, str, str]]:
    """(Zeilennummer, Präfix, Text, Schwanz) der zu prüfenden Zeilen.

    Präfix = Markdown/Nummer/Emoji/Label, Schwanz = Quellenklammer und Link —
    beides bleibt unangetastet, nur der Text dazwischen geht ans Modell.
    """
    result = []
    for i, zeile in enumerate(markdown.splitlines()):
        if zeile.startswith("# "):
            m = re.match(r"^# [^\wÄÖÜäöüß„\"']*", zeile)
        elif re.match(r"## \d", zeile):
            m = re.match(r"^## \d️?⃣?\s*[^\wÄÖÜäöüß„\"'(«»]*", zeile)
        elif zeile.startswith(_WARUM_LABELS):
            m = re.match(r"^\*\*[^*]+\*\*\s*", zeile)
        else:
            continue
        praefix = m.group(0)
        rest = zeile[len(praefix):]
        schwanz = _QUELLE_SCHWANZ_RE.search(rest).group(1)
        text = rest[: len(rest) - len(schwanz)] if schwanz else rest
        if text.strip():
            result.append((i, praefix, text, schwanz))
    return result


def korrektur_zulaessig(alt: str, neu: str) -> bool:
    """Nur kleine Korrekturen: gleiche Zahlen, gleiche Links, hohe Ähnlichkeit."""
    from difflib import SequenceMatcher

    if not isinstance(neu, str) or not neu.strip() or "\n" in neu:
        return False
    if re.findall(r"\d+", alt) != re.findall(r"\d+", neu):
        return False
    if re.findall(r"\]\(([^)]+)\)", alt) != re.findall(r"\]\(([^)]+)\)", neu):
        return False
    return SequenceMatcher(None, alt, neu).ratio() >= MIN_AEHNLICHKEIT


def setze_korrekturen(markdown: str, zeilen: list, korrigiert: list) -> tuple[str, int]:
    """Übernimmt zulässige Korrekturen. → (Markdown, Anzahl geänderter Zeilen)."""
    if not isinstance(korrigiert, list) or len(korrigiert) != len(zeilen):
        return markdown, 0
    lines = markdown.splitlines()
    n = 0
    for (i, praefix, alt, schwanz), neu in zip(zeilen, korrigiert):
        if not isinstance(neu, str):
            continue
        neu = neu.strip()
        # Leerraum am Textende (vor der Quellenklammer) wie im Original
        neu += alt[len(alt.rstrip()):]
        if neu != alt and korrektur_zulaessig(alt, neu):
            lines[i] = praefix + neu + schwanz
            n += 1
    if not n:
        return markdown, 0
    return "\n".join(lines) + ("\n" if markdown.endswith("\n") else ""), n
