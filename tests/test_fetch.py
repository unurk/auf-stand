"""Tests für fetch: Feed-Parsing, Bereinigung, Zeitfenster-Filter."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from copilot import fetch

SAMPLE = (Path(__file__).parent / "sample_feed.xml").read_bytes()


def _mock_get(monkeypatch, status_code=200, content=SAMPLE):
    def fake_get(url, **kwargs):
        return httpx.Response(status_code, content=content, request=httpx.Request("GET", url))
    monkeypatch.setattr(fetch.httpx, "get", fake_get)


def test_fetch_feed_parses_sample(monkeypatch):
    _mock_get(monkeypatch)
    articles, error = fetch.fetch_feed("Politik", "https://example.com/rss", 15)
    assert error is None
    assert len(articles) == 3
    first = articles[0]
    assert first.title == "Nationalrat beschließt Mietpreisbremse für Altbau"
    assert first.ressort == "Politik"
    assert first.id == "a1"
    # HTML-Tags aus der Description sind entfernt
    assert "<p>" not in first.teaser
    assert first.teaser.startswith("Die Koalition")
    assert first.published is not None and first.published.tzinfo is not None


def test_fetch_feed_respects_max_articles(monkeypatch):
    _mock_get(monkeypatch)
    articles, _ = fetch.fetch_feed("Politik", "https://example.com/rss", 2)
    assert len(articles) == 2


def test_fetch_feed_http_error(monkeypatch):
    _mock_get(monkeypatch, status_code=503)
    articles, error = fetch.fetch_feed("Politik", "https://example.com/rss", 15)
    assert articles == []
    assert "503" in error


def test_fetch_feed_network_error(monkeypatch):
    def fake_get(url, **kwargs):
        raise httpx.ConnectTimeout("timeout")
    monkeypatch.setattr(fetch.httpx, "get", fake_get)
    articles, error = fetch.fetch_feed("Politik", "https://example.com/rss", 15)
    assert articles == []
    assert "nicht erreichbar" in error


def test_fetch_all_dedupliziert(monkeypatch):
    _mock_get(monkeypatch)
    config = {"feeds": [
        {"name": "Startseite", "url": "https://example.com/rss"},
        {"name": "Politik", "url": "https://example.com/rss"},
    ]}
    result = fetch.fetch_all(config)
    # Gleiche guids über zwei Feeds → nur einmal
    assert len(result.articles) == 3
    assert result.errors == []


def test_clean_entfernt_tags_und_entities():
    assert fetch._clean("<p>A &amp; B</p>  <br> C") == "A & B C"


def test_author_bereinigt_presse_zusatz():
    entry = {"author": "Von Max Mustermann (Die Presse)"}
    assert fetch._author(entry) == "Max Mustermann"


def test_author_verwirft_email():
    entry = {"author": "redaktion@diepresse.com"}
    assert fetch._author(entry) is None


def test_filter_recent_behaelt_undatiertes():
    now = datetime.now(timezone.utc)
    fresh = fetch.Article("1", "t", "", "", "R", published=now - timedelta(hours=2))
    old = fetch.Article("2", "t", "", "", "R", published=now - timedelta(hours=30))
    undated = fetch.Article("3", "t", "", "", "R", published=None)
    result = fetch.filter_recent([fresh, old, undated], lookback_hours=18)
    assert [a.id for a in result] == ["1", "3"]
