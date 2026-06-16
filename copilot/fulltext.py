"""Volltext-Fetcher für diepresse.com — nutzt PRESSE_COOKIE aus .env."""
from __future__ import annotations

import os
import time

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Selektoren in Prioritätsreihenfolge — erster Treffer gewinnt.
CONTENT_SELECTORS = [
    ("class", "article-body"),
    ("class", "story-content"),
    ("class", "article__body"),
    ("class", "articleBody"),
    ("class", "entry-content"),
    ("itemprop", "articleBody"),
    ("tag", "article"),
]

TIMEOUT = 8
DELAY = 1.5  # Sekunden zwischen Requests


def _cookie_header() -> str | None:
    return os.environ.get("PRESSE_COOKIE") or None


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "de-AT,de;q=0.9",
        "Referer": "https://www.diepresse.com/",
    })
    cookie = _cookie_header()
    if cookie:
        s.headers["Cookie"] = cookie
    return s


def _extract(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    # Störende Elemente entfernen
    for tag in soup.select("script, style, nav, header, footer, aside, .ad, .advertisement, .paywall-hint"):
        tag.decompose()

    for selector_type, value in CONTENT_SELECTORS:
        if selector_type == "tag":
            el = soup.find(value)
        elif selector_type == "class":
            el = soup.find(class_=value)
        elif selector_type == "itemprop":
            el = soup.find(itemprop=value)
        else:
            continue
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text) > 200:
                return text

    return None


def fetch_fulltext(url: str, session: requests.Session) -> str | None:
    """Holt den Volltext einer einzelnen URL. Gibt None bei Fehler zurück."""
    try:
        resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
        if resp.status_code != 200:
            return None
        return _extract(resp.text)
    except Exception:
        return None


def enrich_articles(articles: list) -> None:
    """Ergänzt article.fulltext für alle Artikel — in-place, kein Crash bei Fehlern."""
    if not _cookie_header():
        return

    session = _session()
    for i, article in enumerate(articles):
        if not article.link:
            continue
        if i > 0:
            time.sleep(DELAY)
        article.fulltext = fetch_fulltext(article.link, session)


def test_url(url: str) -> None:
    """CLI-Hilfsfunktion: Gibt Volltext einer einzelnen URL aus."""
    cookie = _cookie_header()
    if not cookie:
        print("PRESSE_COOKIE nicht in .env gesetzt — teste ohne Cookie (nur öffentliche Artikel).")

    session = _session()
    print(f"Fetche {url} ...")
    text = fetch_fulltext(url, session)

    if text is None:
        print("\nKein Volltext extrahiert. Mögliche Ursachen:")
        print("  - Artikel hinter Paywall und kein/falsches Cookie")
        print("  - Selector trifft nicht — HTML-Struktur hat sich geändert")
        print("  - Timeout oder Netzwerkfehler")
    else:
        preview = text[:2000]
        print(f"\nVolltext ({len(text)} Zeichen):\n{'—' * 60}\n{preview}")
        if len(text) > 2000:
            print(f"\n... ({len(text) - 2000} weitere Zeichen)")
