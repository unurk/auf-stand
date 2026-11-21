"""Leserprofil aus Feedback: Welche Themen will Unur öfter, welche seltener?

Datenfluss (alles ohne neues Secret, ohne kostenpflichtigen Dienst):

1. Beim Erzeugen einer Ausgabe merkt sich ``merke_punkt_merkmale`` je Punkt
   seine Merkmale: Themen-Tracker (über das Schlagwort), Ressort (aus der
   Quellenklammer „(Wirtschaft · …)" bzw. den verlinkten Artikeln) und
   Stichwörter aus der Überschrift.
2. Feedback kommt aus zwei Quellen und landet einheitlich in
   ``state["article_feedback"]``:
   - Telegram 👍/👎 je Punkt (Rückkanal, vorhandenes TELEGRAM_BOT_TOKEN);
   - Web „Relevant"/„Weniger": Die Seite zählt jeden Vote zusätzlich auf dem
     freien, cookie-losen Abacus-Zähler (derselbe wie die Engagement-Messung)
     unter „<datum>-<ausgabe>_fb<idx>_<up|down>". ``sync_web_feedback`` liest
     die Zähler der letzten Tage und übernimmt nur das Delta.
3. ``berechne_profil`` verdichtet alle Votes zu Gewichten je Merkmal — mit
   Abklingen (Halbwertszeit 14 Tage), damit alte Votes weniger zählen. Das
   Profil liegt in ``state["leserprofil"]`` (Actions-Cache + State-Backup).
4. ``ordne_material`` sortiert das Material für den Prompt nach Profil-Score
   und lässt stark abgewählte Randmeldungen weg — Top-Nachrichten
   (Startseiten-Feed) bleiben immer drin. ``prompt_block`` sagt dem Modell,
   was bevorzugt bzw. nur bei hoher Materialität gebracht werden soll.

Ohne Feedback ist das Profil leer: Reihenfolge, Material und Prompt bleiben
exakt wie bisher.
"""
from __future__ import annotations

import math
import re
import time
from datetime import date, datetime, timedelta, timezone

HALBWERTSZEIT_TAGE = 14.0
# Merkmals-Arten und wie stark ein Vote auf sie durchschlägt. Stichwörter sind
# verrauscht (ein Titel hat viele Wörter), darum halbes Gewicht.
_ART_FAKTOR = {"thema": 1.0, "ressort": 1.0, "wort": 0.5}
# Ab welchem Score eine Meldung als „abgewählt" gilt und höchstens welcher
# Anteil des Materials deshalb wegfallen darf.
SCHWELLE_WEGLASSEN = -0.5
MAX_ANTEIL_WEGLASSEN = 0.25
# Feeds, deren Meldungen nie wegen des Profils wegfallen (Top-Nachrichten).
TOP_RESSORTS = {"Startseite", "Top Stories", "Home"}
# Wie viele Tage Web-Zähler rückwirkend gelesen werden (Votes kommen meist
# am selben Tag; zwei Tage decken auch Nachzügler ab).
WEB_SYNC_TAGE = 2

_STOPWOERTER = frozenset("""
aber alle allem allen aller alles als also am an ans auch auf aus bei beim bis
da dabei damit dann das dass dem den denn der des dessen die dies diese diesem
diesen dieser dieses doch dort du durch ein eine einem einen einer eines er es
etwa für gegen hat hatte hier ihr ihre im in ins ist ja jetzt kann kein keine
mehr mit nach neue neuen neuer neues nicht noch nun nur ob oder ohne schon sehr
sein seine sich sie sind so soll sollen über um und uns unter vom von vor war
was weil wenn wer wie wieder will wird wo zu zum zur zwischen erst erstmals
bleibt gibt geht kommt macht steht legt zieht setzt bringt drohen droht
heute morgen gestern jahr jahre prozent euro millionen milliarden mio mrd
the and for with from into after over about new says will would could
""".split())
_WORT_RE = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß-]{3,}")
_RESSORT_KLAMMER_RE = re.compile(r"\(([A-ZÄÖÜ][\wÄÖÜäöüß&/ -]{1,30}?)\s*(?:·[^()]*)?\)\.?\s*(?:\[|$)")


# ── Merkmale ─────────────────────────────────────────────────────────────────

def _stamm(wort: str) -> str:
    """Grober Stamm: klein, ohne Bindestrich-Enden, auf 7 Zeichen gekürzt.

    Reicht, damit „Mietrecht"/„Mietrechts" und „Zölle"/„Zöllen" zusammenfallen.
    """
    return wort.lower().strip("-")[:7]


def stichwoerter(text: str, limit: int = 6) -> list[str]:
    result: list[str] = []
    for w in _WORT_RE.findall(text or ""):
        if w.lower() in _STOPWOERTER:
            continue
        s = _stamm(w)
        if len(s) >= 4 and s not in result:
            result.append(s)
        if len(result) >= limit:
            break
    return result


def _themen(text: str, topics: list) -> list[str]:
    from .synthesize import topic_keyword, topic_name

    low = (text or "").lower()
    treffer = []
    for topic in topics or []:
        kw = topic_keyword(topic).lower()
        if not kw:
            continue
        # Wortanfang: „EU" soll nicht in „neue" treffen, „Miet" aber in „Mietrecht".
        if re.search(rf"(?<![\wÄÖÜäöüß]){re.escape(kw)}", low):
            treffer.append(topic_name(topic))
    return treffer


def merkmale(titel: str, text: str = "", ressorts: list[str] | None = None,
             topics: list | None = None) -> list[str]:
    """Merkmals-Schlüssel eines Punkts oder Artikels: thema:…, ressort:…, wort:…"""
    keys: list[str] = []
    for name in _themen(f"{titel} {text}", topics or []):
        keys.append(f"thema:{name}")
    for r in ressorts or []:
        r = r.strip()
        if r and r not in TOP_RESSORTS and f"ressort:{r}" not in keys:
            keys.append(f"ressort:{r}")
    for w in stichwoerter(titel):
        keys.append(f"wort:{w}")
    return keys


def _punkt_bloecke(markdown: str) -> list[tuple[str, str]]:
    """(Überschrift ohne Nummer/Emoji, Fließtext) je nummeriertem Punkt."""
    from .qualitaet import punkt_titel

    titel = punkt_titel(markdown)
    teile = [t for t in re.split(r"(?m)^(?=## |---)", markdown) if re.match(r"## \d", t)]
    return [(t, teile[i].split("\n", 1)[1] if "\n" in teile[i] else "")
            for i, t in enumerate(titel) if i < len(teile)]


def punkt_merkmale_aus_lagebild(markdown: str, articles: list, topics: list) -> list[list[str]]:
    """Merkmale je Punkt der fertigen Ausgabe (Reihenfolge = Punkt-Index)."""
    link_ressort = {a.link: a.ressort for a in articles or [] if getattr(a, "link", "")}
    result = []
    for titel, text in _punkt_bloecke(markdown):
        ressorts: list[str] = []
        m = _RESSORT_KLAMMER_RE.search(text)
        if m:
            ressorts.append(m.group(1).strip())
        for url in re.findall(r"\]\(([^)]+)\)", text):
            r = link_ressort.get(url)
            if r and r not in ressorts:
                ressorts.append(r)
        result.append(merkmale(titel, text, ressorts, topics))
    return result


def merke_punkt_merkmale(state: dict, datum: str, edition: str, merkmale_je_punkt: list) -> None:
    if not merkmale_je_punkt:
        return
    store = state.setdefault("punkt_merkmale", {})
    store[f"{datum}|{edition}"] = merkmale_je_punkt
    cutoff = date.fromisoformat(datum).toordinal() - 60
    state["punkt_merkmale"] = {
        k: v for k, v in store.items()
        if date.fromisoformat(k.split("|")[0]).toordinal() >= cutoff
    }


def merkmale_fuer_vote(state: dict, eintrag: dict) -> list[str]:
    """Merkmale eines Votes: gespeichert, sonst aus dem Punkt-Index, sonst aus dem Titel."""
    if eintrag.get("merkmale"):
        return list(eintrag["merkmale"])
    key = f"{eintrag.get('date', '')}|{eintrag.get('edition', '')}"
    idx = eintrag.get("article_idx", -1)
    je_punkt = state.get("punkt_merkmale", {}).get(key, [])
    if isinstance(idx, int) and 0 <= idx < len(je_punkt):
        return list(je_punkt[idx])
    return merkmale(eintrag.get("heading", ""))


# ── Web-Feedback einsammeln ──────────────────────────────────────────────────

def vote_zaehler_key(datum: str, edition: str, idx: int, vote: str) -> str:
    """Schlüssel wie im Browser: „2026-11-20-morgen_fb3_up"."""
    from .engagement import zaehler_key

    return zaehler_key(datum, edition, f"fb{idx}_{vote}")


def sync_web_feedback(state: dict, config: dict, heute: date | None = None,
                      http_get=None, pause=time.sleep) -> int:
    """Übernimmt neue Web-Votes aus den Abacus-Zählern. → Anzahl neuer Votes.

    Zähler können nur steigen; ``web_feedback_import`` hält fest, was schon
    übernommen wurde, damit jeder Vote genau einmal zählt. Netzfehler → 0,
    der Lauf geht weiter (best-effort).
    """
    from .engagement import lies_zaehler, zaehler_config

    zc = zaehler_config(config)
    if zc is None:
        return 0
    base, ns = zc
    heute = heute or datetime.now().date()
    gueltig = {(heute - timedelta(days=i)).isoformat() for i in range(WEB_SYNC_TAGE)}
    importiert = state.setdefault("web_feedback_import", {})
    neu = 0
    for key, headings in sorted(state.get("edition_points", {}).items()):
        datum, _, edition = key.partition("|")
        if datum not in gueltig:
            continue
        for idx, heading in enumerate(headings):
            for vote in ("up", "down"):
                stand = lies_zaehler(base, ns, vote_zaehler_key(datum, edition, idx, vote),
                                     http_get, pause)
                if http_get is None:
                    pause(0.4)  # Abacus erlaubt 30 Anfragen / 10 s
                if stand is None:
                    continue
                ikey = f"{datum}|{edition}|{idx}"
                bisher = importiert.setdefault(ikey, {}).get(vote, 0)
                for _ in range(max(0, stand - bisher)):
                    _vote_anhaengen(state, datum, edition, idx, heading, vote, "web")
                    neu += 1
                importiert[ikey][vote] = max(stand, bisher)
    cutoff = heute.toordinal() - 60
    state["web_feedback_import"] = {
        k: v for k, v in importiert.items()
        if date.fromisoformat(k.split("|")[0]).toordinal() >= cutoff
    }
    return neu


def _vote_anhaengen(state, datum, edition, idx, heading, rating, quelle) -> None:
    state.setdefault("article_feedback", []).append({
        "date": datum,
        "edition": edition,
        "article_idx": idx,
        "heading": heading,
        "rating": rating,
        "chat_id": quelle,
        "quelle": quelle,
        "merkmale": merkmale_fuer_vote(
            state, {"date": datum, "edition": edition, "article_idx": idx, "heading": heading}
        ),
        "ts": datetime.now(timezone.utc).isoformat(),
    })


# ── Profil ───────────────────────────────────────────────────────────────────

def berechne_profil(state: dict, heute: date | None = None,
                    halbwertszeit: float = HALBWERTSZEIT_TAGE) -> dict:
    """Gewichte je Merkmal aus allen Votes, mit exponentiellem Abklingen.

    Telegram: je Chat und Punkt zählt der LETZTE Tap (Umentscheiden zählt nicht
    doppelt). Web: jeder Zähler-Treffer ist ein eigenes Gerät/eine eigene
    Entscheidung und zählt einzeln.
    """
    heute = heute or datetime.now().date()
    letzte: dict[tuple, dict] = {}
    web: list[dict] = []
    for e in state.get("article_feedback", []):
        if e.get("rating") not in ("up", "down"):
            continue
        if e.get("quelle") == "web":
            web.append(e)
        else:
            letzte[(e.get("chat_id"), e.get("date"), e.get("edition"), e.get("article_idx"))] = e
    gewichte: dict[str, float] = {}
    anzahl = 0
    for e in list(letzte.values()) + web:
        try:
            alter = max(0, heute.toordinal() - date.fromisoformat(e["date"]).toordinal())
        except (KeyError, ValueError):
            continue
        abkling = 0.5 ** (alter / halbwertszeit)
        vorzeichen = 1.0 if e["rating"] == "up" else -1.0
        anzahl += 1
        for key in merkmale_fuer_vote(state, e):
            faktor = _ART_FAKTOR.get(key.split(":", 1)[0], 0.5)
            gewichte[key] = gewichte.get(key, 0.0) + vorzeichen * abkling * faktor
    gewichte = {k: round(v, 3) for k, v in gewichte.items() if abs(v) >= 0.05}
    return {"stand": heute.isoformat(), "votes": anzahl, "gewichte": gewichte}


def aktualisiere_profil(state: dict, heute: date | None = None) -> dict:
    profil = berechne_profil(state, heute)
    state["leserprofil"] = profil
    return profil


def artikel_score(article, profil: dict, topics: list) -> float:
    """Score in (-1, 1): >0 = eher gewünscht, <0 = eher abgewählt, 0 = neutral."""
    gewichte = (profil or {}).get("gewichte") or {}
    if not gewichte:
        return 0.0
    keys = merkmale(article.title, getattr(article, "teaser", ""), [article.ressort], topics)
    summe = sum(gewichte.get(k, 0.0) for k in keys)
    return math.tanh(summe / 2)


def ist_top_nachricht(article) -> bool:
    return getattr(article, "ressort", "") in TOP_RESSORTS


def ordne_material(articles: list, profil: dict, topics: list) -> tuple[list, list]:
    """(Material in Prompt-Reihenfolge, weggelassene Meldungen).

    Ohne Profil-Gewichte: unverändert. Sonst stabil nach Score sortiert;
    Meldungen unter der Schwelle fallen weg — nie Top-Nachrichten, nie mehr
    als ein Viertel des Materials (die am stärksten abgewählten zuerst).
    """
    if not (profil or {}).get("gewichte") or not articles:
        return list(articles), []
    scores = {id(a): artikel_score(a, profil, topics) for a in articles}
    kandidaten = sorted(
        (a for a in articles
         if scores[id(a)] <= SCHWELLE_WEGLASSEN and not ist_top_nachricht(a)),
        key=lambda a: scores[id(a)],
    )
    weg = kandidaten[: int(len(articles) * MAX_ANTEIL_WEGLASSEN)]
    weg_ids = {id(a) for a in weg}
    bleibt = [a for a in articles if id(a) not in weg_ids]
    bleibt.sort(key=lambda a: -scores[id(a)])  # sorted ist stabil: Gleichstand = alte Reihenfolge
    return bleibt, weg


def _lesbar(key: str) -> str:
    art, _, wert = key.partition(":")
    if art == "ressort":
        return f"Ressort {wert}"
    if art == "wort":
        return f"„{wert}…“"
    return wert


def prompt_block(profil: dict, lang: str = "de", limit: int = 5) -> str:
    """Prompt-Abschnitt zum Leserprofil — '' ohne nennenswerte Gewichte."""
    gewichte = (profil or {}).get("gewichte") or {}
    plus = [k for k, v in sorted(gewichte.items(), key=lambda kv: -kv[1]) if v >= 0.3][:limit]
    minus = [k for k, v in sorted(gewichte.items(), key=lambda kv: kv[1]) if v <= -0.3][:limit]
    if not plus and not minus:
        return ""
    if lang == "en":
        zeilen = ["\n\n---\n\n# Reader profile (from feedback, decaying over time)"]
        if plus:
            zeilen.append("Rated relevant more often: " + ", ".join(_lesbar(k) for k in plus)
                          + " — at equal materiality, prefer these and rank them higher.")
        if minus:
            zeilen.append("Rated „less“ more often: " + ", ".join(_lesbar(k) for k in minus)
                          + " — include only if clearly material.")
        zeilen.append("Never drop a top story of the day because of this profile.")
        return "\n".join(zeilen) + "\n"
    zeilen = ["\n\n---\n\n# Leserprofil (aus Feedback, ältere Votes zählen weniger)"]
    if plus:
        zeilen.append("Öfter als relevant markiert: " + ", ".join(_lesbar(k) for k in plus)
                      + " — bei gleicher Materialität bevorzugen und weiter oben bringen.")
    if minus:
        zeilen.append("Öfter mit „Weniger“ markiert: " + ", ".join(_lesbar(k) for k in minus)
                      + " — nur aufnehmen, wenn eindeutig materiell wichtig.")
    zeilen.append(
        "Top-Nachrichten des Tages nie wegen dieses Profils weglassen — das Profil "
        "verschiebt Gewichte, es ersetzt nicht das Auswahlprinzip."
    )
    return "\n".join(zeilen) + "\n"
