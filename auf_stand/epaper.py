"""Stellt den Link zur aktuellen E-Paper-Ausgabe bereit."""
from __future__ import annotations

import urllib.parse

import httpx

_CCIDIST_BASE = "https://digital.diepresse.com/ccidist-ws/dp/dp_die-presse"
_READER_BASE = "https://digital.diepresse.com/ccidist-replica-reader/"
_FALLBACK_URL = "https://digital.diepresse.com"


def get_epaper_url() -> str:
    """Gibt die Reader-URL der aktuellen Ausgabe zurück; fällt auf die Homepage zurück."""
    for endpoint in ("issues/latest", "issues/current"):
        try:
            resp = httpx.get(
                f"{_CCIDIST_BASE}/{endpoint}",
                timeout=5,
                follow_redirects=True,
            )
            if resp.status_code == 200:
                data = resp.json()
                issue_id = data.get("id") or data.get("issueId") or data.get("issue_id")
                if issue_id:
                    epub = f"{_CCIDIST_BASE}/issues/{issue_id}/"
                    return (
                        f"{_READER_BASE}?epub={urllib.parse.quote(epub, safe='')}#/pages/1"
                    )
        except Exception:
            pass
    return _FALLBACK_URL


def epaper_section(url: str) -> str:
    """Gibt den Markdown-Block für den E-Paper-Link zurück."""
    return f"\n---\n\n📰 **Die Presse — E-Paper** · [Heutige Ausgabe öffnen →]({url})"
