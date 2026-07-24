"""Ruhe-Ausgabe: Stille wird zugestellt, nicht verschwiegen."""
from datetime import datetime, timedelta, timezone

from copilot import main
from copilot.fetch import Article, FetchResult

CONFIG = {
    "editions": {
        "morgen": {"label": "Morgen", "time": "06:00", "emoji": "☀️", "lookback_hours": 10},
        "mittag": {"label": "Mittag", "time": "11:00", "emoji": "🌤️", "lookback_hours": 5.5},
        "abend": {"label": "Abend", "time": "20:00", "emoji": "🌙", "lookback_hours": 4.5},
    },
    "telegram_chat_ids": ["42"],
}


def _artikel(n: int) -> list[Article]:
    jetzt = datetime.now(timezone.utc) - timedelta(hours=1)
    return [
        Article(id=f"a{i}", title=f"Titel {i}", teaser="Teaser", link="",
                ressort="Politik", published=jetzt)
        for i in range(n)
    ]


def _patch(monkeypatch, tmp_path, state_dict, artikel):
    monkeypatch.setattr(main.state, "load_state", lambda: state_dict)
    monkeypatch.setattr(main.state, "save_state", lambda s: None)
    monkeypatch.setattr(main, "fetch_all", lambda config: FetchResult(articles=artikel))
    monkeypatch.setattr(main.render, "OUT_DIR", tmp_path)
    gesendet = []
    monkeypatch.setattr(
        main.telegram, "send_telegram",
        lambda md, ids, **kw: gesendet.append(md),
    )
    return gesendet


def test_ruhe_ausgabe_wird_zugestellt(monkeypatch, tmp_path):
    """Alle Artikel bereits gesehen → kurze Ruhe-Meldung statt Schweigen."""
    artikel = _artikel(5)
    st = {"seen": {a.id: "2026-07-24T00:00:00+00:00" for a in artikel}}
    gesendet = _patch(monkeypatch, tmp_path, st, artikel)

    assert main.run_edition("abend", CONFIG, dry_run=False, keep_seen=False) == 0
    assert len(gesendet) == 1
    md = gesendet[0]
    assert "Ruhige Lage" in md
    assert "5 geprüften" in md
    assert "Du bist informiert" in md
    assert "nichts zu tun" in md
    # Als Datei abgelegt, damit die Ausgabe auch im Archiv und in der PWA steht
    assert (tmp_path / f"{datetime.now():%Y-%m-%d}-abend.md").exists()


def test_ruhe_ausgabe_zaehlt_fuer_den_block_guard(monkeypatch, tmp_path):
    """Auch eine Ruhe-Ausgabe ist eine Zustellung — sonst liefe der Block erneut."""
    artikel = _artikel(3)
    st = {"seen": {a.id: "2026-07-24T00:00:00+00:00" for a in artikel}}
    _patch(monkeypatch, tmp_path, st, artikel)

    main.run_edition("abend", CONFIG, dry_run=False, keep_seen=False)
    heute = f"{datetime.now():%Y-%m-%d}"
    assert any(
        s["edition"] == "abend" and s["date"] == heute and s["points"] == 0
        for s in st["stats"]
    )
    assert st["stats"][0]["geprueft"] == 3


def test_ruhe_ausgabe_im_dry_run_ohne_versand(monkeypatch, tmp_path):
    artikel = _artikel(2)
    st = {"seen": {a.id: "x" for a in artikel}}
    gesendet = _patch(monkeypatch, tmp_path, st, artikel)

    assert main.run_edition("abend", CONFIG, dry_run=True, keep_seen=True) == 0
    assert gesendet == []
    assert not list(tmp_path.glob("*.md"))


def test_ruhe_ausgabe_ohne_artikel_nennt_keine_zahl(monkeypatch, tmp_path):
    gesendet = _patch(monkeypatch, tmp_path, {}, [])
    # Leerer Fetch bricht für echte Ausgaben ab (Diagnose-Pfad), nicht Ruhe.
    assert main.run_edition("abend", CONFIG, dry_run=False, keep_seen=True) == 1
    assert gesendet == []
