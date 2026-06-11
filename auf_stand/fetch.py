"""Holt die oeffentlichen RSS-Feeds der Presse und normalisiert die Eintraege."""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import feedparser

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Article:
    id: str
    title: str
    teaser: str
    link: str
    ressort: str
    published: datetime | None
    fulltext: str | None = None

    def age_hours(self) -> float | None:
        if not self.published:
            return None
        return (datetime.now(timezone.utc) - self.published).total_seconds() / 3600


@dataclass
class FetchResult:
    articles: list[Article] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _clean(text: str) -> str:
    text = TAG_RE.sub(" ", text or "")
    return html.unescape(re.sub(r"\s+", " ", text)).strip()


def _parse_date(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
    return None


def fetch_feed(name: str, url: str, max_articles: int) -> tuple[list[Article], str | None]:
    """Holt einen Feed. Liefert (Artikel, Fehlermeldung oder None)."""
    parsed = feedparser.parse(url, agent=USER_AGENT)
    status = getattr(parsed, "status", None)
    if parsed.bozo and not parsed.entries:
        return [], f"{name}: Feed nicht lesbar ({url}, Status {status}, {parsed.bozo_exception})"
    if status and status >= 400:
        return [], f"{name}: HTTP {status} fuer {url}"
    articles: list[Article] = []
    for entry in parsed.entries[:max_articles]:
        link = entry.get("link", "")
        articles.append(
            Article(
                id=entry.get("id") or link,
                title=_clean(entry.get("title", "")),
                teaser=_clean(entry.get("summary", "")),
                link=link,
                ressort=name,
                published=_parse_date(entry),
            )
        )
    return articles, None


def fetch_all(config: dict) -> FetchResult:
    import os
    result = FetchResult()
    max_articles = int(config.get("max_articles_per_feed", 15))
    seen_ids: set[str] = set()
    for feed in config.get("feeds", []):
        articles, error = fetch_feed(feed["name"], feed["url"], max_articles)
        if error:
            result.errors.append(error)
            continue
        for article in articles:
            if article.id in seen_ids:
                continue
            seen_ids.add(article.id)
            result.articles.append(article)

    if os.environ.get("PRESSE_COOKIE"):
        from . import fulltext
        presse_articles = [a for a in result.articles if "diepresse.com" in a.link]
        print(f"Volltext-Fetch für {len(presse_articles)} Presse-Artikel ...")
        fulltext.enrich_articles(presse_articles)
        enriched = sum(1 for a in presse_articles if a.fulltext)
        print(f"  {enriched}/{len(presse_articles)} Volltexte geladen.")

    return result


def filter_recent(articles: list[Article], lookback_hours: float) -> list[Article]:
    """Artikel ohne Datum bleiben drin (lieber zu viel Kontext als zu wenig)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return [a for a in articles if a.published is None or a.published >= cutoff]
