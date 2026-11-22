"""Welche Ausgabe gehört zu diesem Lauf? — aus dem geplanten Slot, nie aus der Uhrzeit.

Hintergrund (21.11.2026): Der GitHub-Cron des 20-Uhr-Slots feuerte erst um 01:08
Wien. Der Workflow leitete die Ausgabe damals aus der aktuellen Uhrzeit ab
(„vor 9 Uhr = morgen"), veröffentlichte den Abend-Lauf als Morgen-Ausgabe — und
der Block-Guard sperrte danach die echte 06-Uhr-Ausgabe.

Regeln jetzt:
- ``workflow_dispatch`` mit ``edition``-Input (cron-job.org, manuell): genau diese
  Ausgabe, ohne Verspätungsprüfung. Manuell muss immer gehen.
- ``schedule``: Die Ausgabe ergibt sich aus dem Cron-Ausdruck, der gefeuert hat
  (``github.event.schedule``). Startet der Lauf mehr als ``MAX_VERSPAETUNG`` nach
  seinem Slot (Wiener Zeit), wird er übersprungen — er belegt und blockiert
  damit keinen anderen Slot.
- ``auto`` (manueller Lauf ohne Input, lokal): Uhrzeit, aber in Wiener Zeit.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

WIEN = ZoneInfo("Europe/Vienna")

# Muss exakt zu den `schedule`-Einträgen in .github/workflows/lagebild.yml passen
# (ein Test prüft das).
CRON_SLOTS = {
    "*/30 4-6 * * *": "morgen",
    "*/30 9-11 * * *": "mittag",
    "*/30 14-16 * * *": "nachmittag",
    "*/30 18-20 * * *": "abend",
    "0 7 * * 6": "woche",
}
# Ein Lauf darf bis zu 3 h nach seinem Slot noch ausliefern. Die Wiederhol-Crons
# eines Fensters liegen höchstens 2,5 h nach dem Slot (Sommerzeit), das reicht.
MAX_VERSPAETUNG = timedelta(hours=3)
# Im Winter (UTC+1) startet das Cron-Fenster eine Stunde VOR der Wiener Slot-Zeit.
MAX_VORLAUF = timedelta(hours=1)


def slot_zeit(edition: str, config: dict, jetzt: datetime) -> datetime | None:
    """Letzter Termin des Slots (Wiener Zeit), zu dem dieser Lauf gehören kann.

    Heute, wenn der Lauf höchstens ``MAX_VORLAUF`` davor startet — sonst gestern.
    """
    zeit = (config.get("editions", {}).get(edition) or {}).get("time")
    if not zeit:
        return None
    h, m = (int(x) for x in str(zeit).split(":"))
    lokal = jetzt.astimezone(WIEN)
    heute = lokal.replace(hour=h, minute=m, second=0, microsecond=0)
    if lokal >= heute - MAX_VORLAUF:
        return heute
    return heute - timedelta(days=1)


def verspaetung(edition: str, config: dict, jetzt: datetime) -> timedelta | None:
    termin = slot_zeit(edition, config, jetzt)
    if termin is None:
        return None
    return jetzt.astimezone(WIEN) - termin


def nach_uhrzeit(jetzt: datetime) -> str:
    """Fallback für ``auto`` (manuell ohne Input): Wiener Uhrzeit, nicht UTC."""
    stunde = jetzt.astimezone(WIEN).hour
    if stunde <= 8:
        return "morgen"
    if stunde <= 13:
        return "mittag"
    if stunde <= 17:
        return "nachmittag"
    return "abend"


def bestimme_ausgabe(schedule: str | None, config: dict,
                     jetzt: datetime | None = None) -> tuple[str | None, str]:
    """Ausgabe für einen geplanten Lauf. → (Ausgabe oder None = überspringen, Begründung)."""
    jetzt = jetzt or datetime.now(timezone.utc)
    schedule = (schedule or "").strip()
    edition = CRON_SLOTS.get(schedule)
    if edition is None:
        return None, f"Unbekannter Cron-Slot '{schedule}' — kein Lauf."
    if edition == "woche":
        return edition, "Wochen-Quittung (Samstags-Slot)."
    spaet = verspaetung(edition, config, jetzt)
    if spaet is None:
        return None, f"Slot '{edition}' fehlt in der Konfiguration — kein Lauf."
    minuten = int(spaet.total_seconds() // 60)
    if spaet > MAX_VERSPAETUNG:
        return None, (
            f"Cron-Slot '{edition}' startet {minuten // 60} h {minuten % 60:02d} min nach "
            f"seinem Termin — zu spät, übersprungen (belegt und blockiert keinen anderen Slot)."
        )
    return edition, f"Cron-Slot '{edition}' ({max(minuten, 0)} min nach Termin)."
