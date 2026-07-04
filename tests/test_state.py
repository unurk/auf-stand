"""Tests für state: Delta-Logik, Dossier, Feedback, Streak."""
from datetime import datetime, timedelta, timezone

from copilot import state
from copilot.fetch import Article


def _art(article_id: str) -> Article:
    return Article(article_id, f"Titel {article_id}", "Teaser", "https://x/{article_id}", "Politik", None)


def test_split_new():
    s = {"seen": {"a": "2026-07-01T00:00:00+00:00"}}
    new, old = state.split_new([_art("a"), _art("b")], s)
    assert [a.id for a in new] == ["b"]
    assert [a.id for a in old] == ["a"]


def test_mark_seen_setzt_last_run():
    s: dict = {}
    state.mark_seen([_art("a")], s, "morgen")
    assert "a" in s["seen"]
    assert "morgen" in s["last_run"]


def test_update_dossier_ordnet_zeile_dem_tracker_zu():
    lagebild = (
        "# Lagebild\n\n"
        "## 1️⃣ Punkt\n\n"
        "## Deine Themen\n"
        "- **EZB:** Seit deinem letzten Stand: Leitzins um 25 Basispunkte gesenkt. [→ Artikel](https://x)\n"
        "\n---\n✅ Du bist informiert\n"
    )
    topics = [{"name": "EZB-Zinsentscheidungen", "schlagwort": "EZB"}]
    s: dict = {}
    state.update_dossier(s, lagebild, topics, "2026-07-04")
    entries = s["dossier"]["EZB-Zinsentscheidungen"]
    assert len(entries) == 1
    assert entries[0]["date"] == "2026-07-04"
    # Markdown, Link und Label-Präfixe sind entfernt
    summary = entries[0]["summary"]
    assert "**" not in summary and "https" not in summary
    assert "Leitzins" in summary


def test_update_dossier_ohne_themen_abschnitt():
    s: dict = {}
    state.update_dossier(s, "# Lagebild\n## 1️⃣ Punkt\nText", [{"name": "EZB", "schlagwort": "EZB"}], "2026-07-04")
    assert "dossier" not in s


def test_strip_markdown():
    line = "- **EZB:** Seit deinem letzten Stand: Zins gesenkt. [→ Artikel](https://x)"
    assert state._strip_markdown(line) == "Zins gesenkt."


def test_feedback_summary_letzte_bewertung_zaehlt():
    s: dict = {}
    state.record_feedback(s, "2026-07-04", "morgen", "down", "1")
    state.record_feedback(s, "2026-07-04", "morgen", "up", "1")  # überschreibt
    state.record_feedback(s, "2026-07-04", "abend", "down", "1")
    summary = state.feedback_summary(s, "2026-07-01")
    assert summary == {"up": 1, "down": 1, "total": 2}


def test_article_feedback_hint_warnt_bei_vielen_downvotes():
    s: dict = {}
    today = datetime.now(timezone.utc).date().isoformat()
    for i in range(4):
        state.record_article_feedback(s, today, "morgen", i, "down", "1")
    hint = state.article_feedback_hint(s, "2026-01-01")
    assert "nicht relevant" in hint


def test_article_feedback_hint_braucht_mindestmenge():
    s: dict = {}
    today = datetime.now(timezone.utc).date().isoformat()
    state.record_article_feedback(s, today, "morgen", 0, "down", "1")
    assert state.article_feedback_hint(s, "2026-01-01") == ""


def test_current_streak():
    today = datetime.now(timezone.utc).date()
    s = {"stats": [
        {"date": (today - timedelta(days=d)).isoformat()} for d in (0, 1, 2, 4)
    ]}
    assert state.current_streak(s) == 3


def test_push_subscription_dedupliziert():
    s: dict = {}
    sub = {"endpoint": "https://push/x", "keys": {}}
    state.add_push_subscription(s, sub)
    state.add_push_subscription(s, sub)
    assert len(s["push_subscriptions"]) == 1
    state.remove_push_subscription(s, "https://push/x")
    assert s["push_subscriptions"] == []
