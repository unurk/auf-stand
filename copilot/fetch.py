"""Holt die oeffentlichen RSS-Feeds der Presse und normalisiert die Eintraege."""
from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import feedparser
import httpx

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
    author: str | None = None

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


def _author(entry) -> str | None:
    """Autor aus dem Feed-Eintrag (dc:creator/author), bereinigt. None wenn leer."""
    raw = entry.get("author")
    if not raw:
        authors = entry.get("authors")
        if authors and isinstance(authors, list):
            raw = authors[0].get("name") if isinstance(authors[0], dict) else None
    if not raw:
        return None
    name = _clean(raw)
    # E-Mail-Adressen verwerfen, „(Die Presse)"-Zusatz und führendes „Von " entfernen.
    name = re.sub(r"\S+@\S+", "", name)
    name = re.sub(r"\((?:die\s+)?presse\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"^[Vv]on\s+", "", name).strip(" ·,–—")
    return name or None


def _parse_date(entry) -> datetime | None:
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
    return None


def fetch_feed(name: str, url: str, max_articles: int) -> tuple[list[Article], str | None]:
    """Holt einen Feed. Liefert (Artikel, Fehlermeldung oder None).

    HTTP läuft über httpx mit Timeout — feedparser.parse(url) hätte keinen und
    ein hängender Feed würde sonst den ganzen Lauf blockieren.
    """
    try:
        resp = httpx.get(
            url, headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True
        )
    except httpx.HTTPError as exc:
        return [], f"{name}: Feed nicht erreichbar ({url}, {exc})"
    if resp.status_code >= 400:
        return [], f"{name}: HTTP {resp.status_code} fuer {url}"
    parsed = feedparser.parse(resp.content)
    if parsed.bozo and not parsed.entries:
        return [], f"{name}: Feed nicht lesbar ({url}, {parsed.bozo_exception})"
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
                author=_author(entry),
            )
        )
    return articles, None


def fetch_all(config: dict) -> FetchResult:
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

    return result


def filter_recent(articles: list[Article], lookback_hours: float) -> list[Article]:
    """Artikel ohne Datum bleiben drin (lieber zu viel Kontext als zu wenig)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return [a for a in articles if a.published is None or a.published >= cutoff]
