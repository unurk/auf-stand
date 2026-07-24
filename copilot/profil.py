"""Wirkungs-Profil: von „interessiert dich das?" zu „wie bist du betroffen?".

Die Themen-Tracker in config.yaml fragen nach Interesse — das ist ein Ressort-Abo.
Dieses Profil fragt nach Exposition: Miete oder Eigentum, Kredit variabel oder fix,
womit geheizt und gependelt wird. Damit kann die Synthese in „Warum es zählt"
konkret werden („für deinen variablen Kredit heißt das …"), statt Relevanz nur
zu behaupten.

Bewusst KEINE Klick-Personalisierung: Die Nutzerin deklariert diese Angaben
selbst, sie werden nicht aus Verhalten erschlossen. Und sie steuern nur die
*Einordnung* — nie die Auswahl der Entwicklungen. Was wichtig ist, bleibt für
alle gleich; nur die Folgen werden persönlich beziffert.

Zehn Fragen, einmalig, jederzeit änderbar (/profil) oder löschbar (/profil loeschen).
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

# Jede Frage: key, Frage-Text, Antwortoptionen (Wert, Button-Label, Prompt-Satz).
# Der Prompt-Satz ist das, was die Synthese später als Kontext sieht — er ist
# bewusst als Aussage über die Nutzerin formuliert.
FRAGEN: list[dict] = [
    {
        "key": "wohnen",
        "frage": "Wie wohnst du?",
        "optionen": [
            ("miete", "Miete", "wohnt zur Miete"),
            ("eigentum_kredit", "Eigentum mit Kredit", "wohnt im Eigentum und zahlt einen Wohnkredit ab"),
            ("eigentum", "Eigentum, abbezahlt", "wohnt im abbezahlten Eigentum"),
        ],
    },
    {
        "key": "kredit",
        "frage": "Hast du einen Kredit — und wie verzinst?",
        "optionen": [
            ("variabel", "Variabel verzinst", "hat einen variabel verzinsten Kredit (Leitzinsänderungen schlagen direkt durch)"),
            ("fix", "Fix verzinst", "hat einen fix verzinsten Kredit (Leitzinsänderungen wirken erst bei Anschlussfinanzierung)"),
            ("keiner", "Keinen Kredit", "hat keinen laufenden Kredit"),
        ],
    },
    {
        "key": "kredithoehe",
        "frage": "Wie hoch ist die offene Kreditsumme ungefähr?",
        "nur_wenn": ("kredit", ("variabel", "fix")),
        "optionen": [
            ("bis100", "bis 100.000 €", "offene Kreditsumme bis rund 100.000 €"),
            ("100_300", "100.000–300.000 €", "offene Kreditsumme zwischen rund 100.000 und 300.000 €"),
            ("ueber300", "über 300.000 €", "offene Kreditsumme über rund 300.000 €"),
        ],
    },
    {
        "key": "beruf",
        "frage": "Wie arbeitest du?",
        "optionen": [
            ("angestellt", "Angestellt", "ist angestellt"),
            ("selbststaendig", "Selbstständig", "ist selbstständig bzw. Unternehmerin oder Unternehmer"),
            ("oeffentlich", "Öffentlicher Dienst", "arbeitet im öffentlichen Dienst"),
            ("pension", "In Pension", "ist in Pension"),
        ],
    },
    {
        "key": "branche",
        "frage": "In welchem Umfeld?",
        "optionen": [
            ("export", "Industrie / Export", "arbeitet in Industrie oder Export (Zölle und Konjunktur schlagen direkt durch)"),
            ("handel", "Handel / Gewerbe", "arbeitet im Handel oder Gewerbe"),
            ("dienstleistung", "Dienstleistung", "arbeitet im Dienstleistungssektor"),
            ("tech", "IT / Tech", "arbeitet in IT oder Tech"),
            ("gesundheit", "Gesundheit / Bildung", "arbeitet im Gesundheits- oder Bildungsbereich"),
        ],
    },
    {
        "key": "mobilitaet",
        "frage": "Wie bist du unterwegs?",
        "optionen": [
            ("diesel", "Auto (Diesel)", "fährt Diesel (Spritpreise wirken unmittelbar)"),
            ("benzin", "Auto (Benzin)", "fährt Benzin (Spritpreise wirken unmittelbar)"),
            ("eauto", "E-Auto", "fährt ein E-Auto (Strompreise und Ladeinfrastruktur zählen)"),
            ("oeffi", "Öffis / Rad", "ist mit Öffis oder Rad unterwegs"),
        ],
    },
    {
        "key": "heizen",
        "frage": "Womit heizt du?",
        "optionen": [
            ("gas", "Gas", "heizt mit Gas (Gaspreis und Netzentgelte wirken direkt)"),
            ("strom", "Strom / Wärmepumpe", "heizt mit Strom oder Wärmepumpe"),
            ("fernwaerme", "Fernwärme", "bezieht Fernwärme"),
            ("holz", "Holz / Pellets", "heizt mit Holz oder Pellets"),
        ],
    },
    {
        "key": "geld",
        "frage": "Wo liegt dein Erspartes?",
        "optionen": [
            ("depot", "Depot / ETF / Aktien", "hat Geld in Aktien, ETFs oder einem Depot (Börsen- und Zinsbewegungen zählen)"),
            ("sparbuch", "Sparbuch / Konto", "hat Erspartes am Sparbuch oder Konto (Inflation und Sparzinsen zählen)"),
            ("immobilie", "In Immobilien", "hat Vermögen in Immobilien gebunden"),
            ("nichts", "Kaum Erspartes", "hat kaum Erspartes"),
        ],
    },
    {
        "key": "kinder",
        "frage": "Kinder im Haushalt?",
        "optionen": [
            ("keine", "Keine", "hat keine Kinder im Haushalt"),
            ("klein", "Klein- / Kindergartenkind", "hat ein Klein- oder Kindergartenkind"),
            ("schule", "Schulkind", "hat ein Schulkind"),
            ("studium", "In Ausbildung / Studium", "hat ein Kind in Ausbildung oder Studium"),
        ],
    },
    {
        "key": "bundesland",
        "frage": "Wo lebst du?",
        "optionen": [
            ("w", "Wien", "lebt in Wien"),
            ("noe", "Niederösterreich", "lebt in Niederösterreich"),
            ("ooe", "Oberösterreich", "lebt in Oberösterreich"),
            ("stmk", "Steiermark", "lebt in der Steiermark"),
            ("tirol", "Tirol / Vorarlberg", "lebt in Tirol oder Vorarlberg"),
            ("sued", "Kärnten / Salzburg / Bgld.", "lebt in Kärnten, Salzburg oder dem Burgenland"),
        ],
    },
]

FRAGEN_NACH_KEY = {f["key"]: f for f in FRAGEN}


def _gilt(frage: dict, antworten: dict) -> bool:
    """Bedingte Fragen (z. B. Kredithöhe nur, wenn es einen Kredit gibt)."""
    cond = frage.get("nur_wenn")
    if not cond:
        return True
    key, erlaubte = cond
    return antworten.get(key) in erlaubte


def get_profil(state: dict) -> dict:
    return state.get("profil", {}).get("antworten", {}) or {}


def naechste_frage(antworten: dict) -> dict | None:
    """Erste noch offene (und zutreffende) Frage — None, wenn das Profil steht."""
    for frage in FRAGEN:
        if frage["key"] in antworten or not _gilt(frage, antworten):
            continue
        return frage
    return None


def fortschritt(antworten: dict) -> tuple[int, int]:
    """(beantwortet, insgesamt zutreffend) — für „Frage 3 von 9"."""
    zutreffend = [f for f in FRAGEN if _gilt(f, antworten)]
    beantwortet = sum(1 for f in zutreffend if f["key"] in antworten)
    return beantwortet, len(zutreffend)


def antwort_speichern(state: dict, key: str, value: str) -> bool:
    """Übernimmt eine Antwort. False, wenn Frage oder Wert unbekannt sind."""
    frage = FRAGEN_NACH_KEY.get(key)
    if not frage or value not in {v for v, _l, _s in frage["optionen"]}:
        return False
    profil = state.setdefault("profil", {})
    antworten = profil.setdefault("antworten", {})
    antworten[key] = value
    # Bedingt gewordene Antworten aufräumen (z. B. Kredithöhe nach „keinen Kredit").
    for f in FRAGEN:
        if not _gilt(f, antworten):
            antworten.pop(f["key"], None)
    profil["ts"] = datetime.now(timezone.utc).isoformat()
    return True


def profil_loeschen(state: dict) -> None:
    state.pop("profil", None)


def aus_code(payload: str) -> dict:
    """Dekodiert den base64-Code aus der PWA (gleiches Muster wie /push)."""
    pad = "=" * (-len(payload) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload + pad))
    if not isinstance(data, dict):
        raise ValueError("Kein Profil-Objekt")
    return {
        k: v for k, v in data.items()
        if k in FRAGEN_NACH_KEY and v in {o[0] for o in FRAGEN_NACH_KEY[k]["optionen"]}
    }


def code_uebernehmen(state: dict, payload: str) -> int:
    """Übernimmt ein komplettes Profil aus der PWA. Liefert die Anzahl Antworten."""
    antworten = aus_code(payload)
    if not antworten:
        return 0
    state["profil"] = {
        "antworten": antworten,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    return len(antworten)


def klartext(antworten: dict) -> list[str]:
    """Die Antworten als lesbare Sätze („wohnt zur Miete", …)."""
    saetze = []
    for frage in FRAGEN:
        wert = antworten.get(frage["key"])
        if not wert or not _gilt(frage, antworten):
            continue
        for v, _label, satz in frage["optionen"]:
            if v == wert:
                saetze.append(satz)
                break
    return saetze


def kurzfassung(antworten: dict) -> str:
    """Eine Zeile für Bestätigungen im Chat."""
    labels = []
    for frage in FRAGEN:
        wert = antworten.get(frage["key"])
        if not wert or not _gilt(frage, antworten):
            continue
        for v, label, _satz in frage["optionen"]:
            if v == wert:
                labels.append(label)
                break
    return " · ".join(labels) if labels else "leer"


def prompt_block(antworten: dict, lang: str = "de") -> str:
    """Profil-Abschnitt für den Synthese-Prompt — '' wenn kein Profil da ist."""
    saetze = klartext(antworten)
    if not saetze:
        return ""
    if lang == "en":
        lines = "\n".join(f"- The reader {s}" for s in saetze)
        return (
            "\n\n---\n\n# Reader profile (impact, not interest)\n"
            f"{lines}\n\n"
            "Use this ONLY to make consequences concrete, never to select stories. "
            "Where the material supports it, add one line to a point:\n"
            "**What it means for you:** [one sentence, concrete, with a number if "
            "the material provides one].\n"
            "Never invent numbers, and skip the line when the profile adds nothing.\n"
        )
    lines = "\n".join(f"- Die Leserin {s}" for s in saetze)
    return (
        "\n\n---\n\n# Wirkungs-Profil der Leserin (Betroffenheit, nicht Interesse)\n"
        f"{lines}\n\n"
        "Nutze das AUSSCHLIESSLICH, um Folgen konkret zu machen — niemals zur Auswahl "
        "der Themen. Wo das Material es hergibt, hänge an einen Punkt eine Zeile:\n"
        "**Für dich konkret:** [ein Satz, konkret, mit Zahl, wenn das Material eine liefert].\n"
        "Erfinde nie Zahlen oder Beträge. Lass die Zeile weg, wenn das Profil nichts "
        "beiträgt — lieber keine Zeile als eine hohle.\n"
    )
