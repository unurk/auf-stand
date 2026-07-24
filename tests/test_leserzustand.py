"""Lese-Signale, Streak und „hat gefehlt"-Rückmeldungen."""
from datetime import date, datetime, timedelta, timezone

from copilot import state as state_mod


def _tag(offset: int) -> str:
    return (date.today() - timedelta(days=offset)).isoformat()


def test_record_read_haelt_signal_fest():
    st: dict = {}
    state_mod.record_read(st, "telegram_tap", "2026-07-24", "abend")
    assert len(st["read_events"]) == 1
    assert st["read_events"][0]["quelle"] == "telegram_tap"
    assert st["read_events"][0]["edition"] == "abend"


def test_read_streak_zaehlt_aufeinanderfolgende_tage():
    st = {"read_events": [{"date": _tag(i)} for i in range(3)]}
    assert state_mod.read_streak(st) == 3
    # Lücke bricht den Streak
    st = {"read_events": [{"date": _tag(0)}, {"date": _tag(2)}]}
    assert state_mod.read_streak(st) == 1


def test_read_streak_zaehlt_ab_gestern_wenn_heute_offen():
    st = {"read_events": [{"date": _tag(1)}, {"date": _tag(2)}]}
    assert state_mod.read_streak(st) == 2


def test_streak_faellt_ohne_lesesignale_auf_zustellung_zurueck():
    st = {"stats": [{"date": _tag(0)}, {"date": _tag(1)}]}
    tage, misst_lesen = state_mod.streak(st)
    assert tage == 2 and misst_lesen is False
    # Sobald gelesen wird, zählt nur noch das
    state_mod.record_read(st, "fb")
    tage, misst_lesen = state_mod.streak(st)
    assert tage == 1 and misst_lesen is True


def test_missing_feedback_wird_notiert_und_kalibriert():
    st: dict = {}
    state_mod.record_missing_feedback(st, "Nichts zur Pensionsreform", "123")
    state_mod.record_missing_feedback(st, "   ", "123")  # leer wird ignoriert
    assert len(st["missing_feedback"]) == 1
    hinweis = state_mod.missing_feedback_hint(st, _tag(30))
    assert "Pensionsreform" in hinweis
    assert "großzügiger" in hinweis


def test_missing_feedback_hint_leer_ohne_meldungen():
    assert state_mod.missing_feedback_hint({}, _tag(30)) == ""


def test_alte_lese_ereignisse_werden_beschnitten():
    alt = (datetime.now(timezone.utc).date() - timedelta(days=90)).isoformat()
    st = {"read_events": [{"date": alt, "quelle": "alt"}]}
    state_mod.record_read(st, "neu")
    assert all(e["date"] != alt for e in st["read_events"])


def test_record_stats_haelt_lesezeit_und_pruefzahl():
    st: dict = {}
    state_mod.record_stats(st, "abend", 3, 420, 12, secs=105, geprueft=62)
    eintrag = st["stats"][0]
    assert eintrag["secs"] == 105
    assert eintrag["geprueft"] == 62
    assert state_mod.letzte_lesezeiten(st) == [105]
