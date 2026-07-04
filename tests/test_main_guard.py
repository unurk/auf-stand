"""Tests für den Block-Guard in main.run_edition — das „keine Doppelzustellung"-Versprechen."""
from datetime import datetime

import pytest

from copilot import main
from copilot.fetch import FetchResult

CONFIG = {
    "editions": {
        "morgen": {"label": "Morgen", "time": "06:00", "lookback_hours": 10},
        "mittag": {"label": "Mittag", "time": "11:00", "lookback_hours": 5.5},
        "nachmittag": {"label": "Nachmittag", "time": "16:00", "lookback_hours": 5.5},
        "abend": {"label": "Abend", "time": "20:00", "lookback_hours": 4.5},
    },
}


def _state_mit_zustellung(edition: str) -> dict:
    return {"stats": [{"date": f"{datetime.now():%Y-%m-%d}", "edition": edition}]}


def test_guard_blockt_niederrangige_ausgabe(monkeypatch):
    """Nachmittag ist raus → ein verspäteter Mittags-Cron darf nichts mehr liefern."""
    monkeypatch.setattr(main.state, "load_state", lambda: _state_mit_zustellung("nachmittag"))
    monkeypatch.setattr(
        main, "fetch_all",
        lambda config: pytest.fail("Guard muss VOR dem Fetch greifen"),
    )
    assert main.run_edition("mittag", CONFIG, dry_run=True, keep_seen=True) == 0


def test_guard_blockt_wiederholungslauf(monkeypatch):
    """Zweiter Cron im selben Fenster: gleicher Block darf nicht doppelt raus."""
    monkeypatch.setattr(main.state, "load_state", lambda: _state_mit_zustellung("mittag"))
    monkeypatch.setattr(
        main, "fetch_all",
        lambda config: pytest.fail("Guard muss VOR dem Fetch greifen"),
    )
    assert main.run_edition("mittag", CONFIG, dry_run=True, keep_seen=True) == 0


def test_guard_laesst_hoeherrangige_ausgabe_durch(monkeypatch):
    """Nach der Mittags-Ausgabe muss der Nachmittag weiter möglich sein."""
    monkeypatch.setattr(main.state, "load_state", lambda: _state_mit_zustellung("mittag"))
    monkeypatch.setattr(main, "fetch_all", lambda config: FetchResult())
    # Leerer Fetch → Abbruch mit 1, aber erst NACH dem Guard (Fetch wurde erreicht).
    assert main.run_edition("nachmittag", CONFIG, dry_run=True, keep_seen=True) == 1


def test_guard_ignoriert_gestrige_zustellungen(monkeypatch):
    state = {"stats": [{"date": "2020-01-01", "edition": "abend"}]}
    monkeypatch.setattr(main.state, "load_state", lambda: state)
    monkeypatch.setattr(main, "fetch_all", lambda config: FetchResult())
    assert main.run_edition("morgen", CONFIG, dry_run=True, keep_seen=True) == 1


def test_unbekannte_ausgabe():
    assert main.run_edition("mitternacht", CONFIG, dry_run=True, keep_seen=True) == 1
