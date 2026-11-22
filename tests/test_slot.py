"""Slot-Bestimmung: Ausgabe aus dem geplanten Cron-Slot, nie aus der Uhrzeit.

Vorfall 21.11.2026: Der 20-Uhr-Cron feuerte erst um 01:08 Wien, lief als
Morgen-Ausgabe, und der Block-Guard sperrte danach die echte 06-Uhr-Ausgabe.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from copilot import main, slot
from copilot.fetch import FetchResult

CONFIG = {
    "editions": {
        "morgen": {"label": "Morgen", "time": "06:00", "lookback_hours": 30},
        "mittag": {"label": "Mittag", "time": "11:00", "lookback_hours": 5.5},
        "nachmittag": {"label": "Nachmittag", "time": "16:00", "lookback_hours": 5.5},
        "abend": {"label": "Abend", "time": "20:00", "lookback_hours": 4.5},
    },
}
ABEND = "*/30 18-20 * * *"
MORGEN = "*/30 4-6 * * *"


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


# ── Der Vorfall vom 21.11. ───────────────────────────────────────────────────

def test_verspaeteter_abendlauf_um_0108_wird_keine_morgen_ausgabe():
    # 21.11.2026 00:08 UTC = 01:08 Wien (Winterzeit), gefeuert hat der Abend-Cron
    edition, grund = slot.bestimme_ausgabe(ABEND, CONFIG, utc(2026, 11, 21, 0, 8))
    assert edition is None
    assert "abend" in grund and "zu spät" in grund


def test_sechs_uhr_lauf_laeuft_danach_normal():
    # 05:00 UTC = 06:00 Wien: der echte Morgen-Slot
    assert slot.bestimme_ausgabe(MORGEN, CONFIG, utc(2026, 11, 21, 5, 0))[0] == "morgen"


def test_vorfall_ende_zu_ende_ueber_cli(monkeypatch):
    """Verspäteter Abend-Cron liefert nichts aus und hinterlässt keinen Stand,
    der den Morgen-Slot sperrt; der 06-Uhr-Lauf geht danach durch den Guard."""
    gelaufen = []
    zustand = {"stats": []}

    def fake_run(edition, config, dry_run, keep_seen):
        gelaufen.append(edition)
        zustand["stats"].append({"date": "2026-11-21", "edition": edition})
        return 0

    monkeypatch.setattr(main, "load_config", lambda path: CONFIG)
    monkeypatch.setattr(main, "run_edition", fake_run)

    original = slot.bestimme_ausgabe

    def lauf(schedule, jetzt):
        monkeypatch.setattr(slot, "bestimme_ausgabe", lambda s, c, j=None: original(s, c, jetzt))
        monkeypatch.setattr(sys, "argv", ["copilot", "slot", "--schedule", schedule])
        return main.main()

    assert lauf(ABEND, utc(2026, 11, 21, 0, 8)) == 0
    assert gelaufen == [] and zustand["stats"] == []
    assert lauf(MORGEN, utc(2026, 11, 21, 5, 0)) == 0
    assert gelaufen == ["morgen"]


def test_guard_sperrt_morgen_nicht_ohne_zustellung(monkeypatch):
    """Ohne Morgen-Stat lässt der Block-Guard den 06-Uhr-Lauf bis zum Fetch durch."""
    # Stand nach dem übersprungenen Abend-Cron: keine Zustellung heute
    monkeypatch.setattr(main.state, "load_state", lambda: {"stats": []})
    geholt = []
    monkeypatch.setattr(main, "fetch_all", lambda config: geholt.append(1) or FetchResult())
    main.run_edition("morgen", CONFIG, dry_run=True, keep_seen=True)
    assert geholt == [1]


# ── Normale und grenzwertige Läufe ──────────────────────────────────────────

def test_puenktliche_slots_im_winter_und_sommer():
    # Winter (UTC+1): 18:00 UTC = 19:00 Wien — Fenster startet 1 h vor dem Slot
    assert slot.bestimme_ausgabe(ABEND, CONFIG, utc(2026, 11, 21, 18, 0))[0] == "abend"
    # Sommer (UTC+2): letzter Wiederhol-Cron 20:30 UTC = 22:30 Wien, 2,5 h nach Slot
    assert slot.bestimme_ausgabe(ABEND, CONFIG, utc(2026, 7, 21, 20, 30))[0] == "abend"
    assert slot.bestimme_ausgabe("*/30 9-11 * * *", CONFIG, utc(2026, 11, 21, 10, 0))[0] == "mittag"
    assert slot.bestimme_ausgabe("*/30 14-16 * * *", CONFIG, utc(2026, 11, 21, 16, 30))[0] == "nachmittag"


def test_grenze_drei_stunden():
    # 20:00 Wien + 2:59 = 22:59 Wien = 21:59 UTC (Winter)
    assert slot.bestimme_ausgabe(ABEND, CONFIG, utc(2026, 11, 21, 21, 59))[0] == "abend"
    assert slot.bestimme_ausgabe(ABEND, CONFIG, utc(2026, 11, 21, 22, 1))[0] is None


def test_verspaeteter_morgen_lauf_wird_nicht_mittag():
    # Morgen-Cron feuert erst 10:30 Wien: weder Morgen (zu spät) noch Mittag
    edition, _ = slot.bestimme_ausgabe(MORGEN, CONFIG, utc(2026, 11, 21, 9, 30))
    assert edition is None


def test_woche_und_unbekannter_slot():
    assert slot.bestimme_ausgabe("0 7 * * 6", CONFIG, utc(2026, 11, 21, 7, 0))[0] == "woche"
    assert slot.bestimme_ausgabe("5 5 * * *", CONFIG, utc(2026, 11, 21, 5, 5))[0] is None
    assert slot.bestimme_ausgabe("", CONFIG, utc(2026, 11, 21, 5, 5))[0] is None


def test_auto_nutzt_wiener_zeit():
    # 07:30 UTC = 08:30 Wien → morgen; 08:30 UTC = 09:30 Wien → mittag
    assert slot.nach_uhrzeit(utc(2026, 11, 21, 7, 30)) == "morgen"
    assert slot.nach_uhrzeit(utc(2026, 11, 21, 8, 30)) == "mittag"
    assert slot.nach_uhrzeit(utc(2026, 11, 21, 19, 0)) == "abend"


def test_manueller_lauf_mit_ausgabe_ohne_verspaetungspruefung(monkeypatch):
    gelaufen = []
    monkeypatch.setattr(main, "load_config", lambda path: CONFIG)
    monkeypatch.setattr(main, "run_edition", lambda e, c, d, k: gelaufen.append(e) or 0)
    monkeypatch.setattr(sys, "argv", ["copilot", "abend"])
    assert main.main() == 0 and gelaufen == ["abend"]


# ── Workflows und Slot-Tabelle passen zusammen ──────────────────────────────

def _crons(datei):
    wf = yaml.safe_load(Path(__file__).resolve().parent.parent.joinpath(
        ".github", "workflows", datei).read_text(encoding="utf-8"))
    triggers = wf.get("on") or wf.get(True)
    return [c["cron"] for c in triggers["schedule"]]


def test_jeder_workflow_cron_hat_einen_slot():
    for datei in ("lagebild.yml", "nyt.yml"):
        for cron in _crons(datei):
            assert cron in slot.CRON_SLOTS, f"{datei}: Cron '{cron}' fehlt in slot.CRON_SLOTS"


def test_workflows_leiten_nicht_mehr_aus_uhrzeit_ab():
    for datei in ("lagebild.yml", "nyt.yml"):
        text = Path(__file__).resolve().parent.parent.joinpath(
            ".github", "workflows", datei).read_text(encoding="utf-8")
        assert "date -u +%H" not in text
        assert 'slot --schedule "$SCHEDULE"' in text
