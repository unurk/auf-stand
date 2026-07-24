"""Wochen-Quittung: misst Wirkung (Time-to-Informed), nicht Produktion."""
from datetime import date, timedelta

from copilot import quittung


def _tag(offset: int) -> str:
    return (date.today() - timedelta(days=offset)).isoformat()


def _stats(**kw):
    basis = {"points": 3, "words": 400, "new_articles": 12, "secs": 105, "geprueft": 60}
    basis.update(kw)
    return basis


def test_zeit_label():
    assert quittung._zeit_label(45) == "45 Sek"
    assert quittung._zeit_label(400) == "6:40 Min"
    assert quittung._zeit_label(0) == "0 Sek"


def test_week_stats_rechnet_time_to_informed():
    state = {"stats": [
        {"date": _tag(0), "edition": "morgen", **_stats()},
        {"date": _tag(1), "edition": "abend", **_stats(secs=135, geprueft=40)},
    ]}
    stats = quittung.week_stats(state)
    assert stats["sekunden"] == 240
    assert stats["zeit_label"] == "4:00 Min"
    assert stats["geprueft"] == 100
    assert stats["points"] == 6


def test_week_stats_faellt_auf_wortzahl_zurueck():
    """Altbestand ohne `secs` darf die Quittung nicht auf 0 setzen."""
    state = {"stats": [{"date": _tag(0), "edition": "morgen", "points": 3,
                        "words": 400, "new_articles": 10}]}
    stats = quittung.week_stats(state)
    assert stats["sekunden"] == 120  # 400 Wörter bei 200 W/min
    assert stats["geprueft"] == 10   # Rückfall auf new_articles


def test_lese_tage_schlagen_zustell_tage():
    state = {
        "stats": [{"date": _tag(i), "edition": "morgen", **_stats()} for i in range(5)],
        "read_events": [{"date": _tag(0)}, {"date": _tag(2)}],
    }
    stats = quittung.week_stats(state)
    assert stats["days_on_stand"] == 2
    assert stats["misst_lesen"] is True


def test_ohne_lesesignale_bleibt_zustellbild():
    state = {"stats": [{"date": _tag(i), "edition": "morgen", **_stats()} for i in range(3)]}
    stats = quittung.week_stats(state)
    assert stats["days_on_stand"] == 3
    assert stats["misst_lesen"] is False


def test_keine_daten_keine_quittung():
    assert quittung.week_stats({}) is None
    assert quittung.week_stats({"stats": [{"date": _tag(30), "edition": "morgen", **_stats()}]}) is None


def test_bild_wird_gezeichnet(tmp_path):
    state = {"stats": [{"date": _tag(i), "edition": "morgen", **_stats()} for i in range(3)]}
    pfad = quittung.build_image(quittung.week_stats(state), tmp_path / "q.png")
    assert pfad.exists() and pfad.stat().st_size > 5000
