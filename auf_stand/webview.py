"""Baut die statische Web-Ansicht (site/) aus den erzeugten Lagebildern."""
from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

from .render import OUT_DIR
from .vorausschau import MONTHS, WEEKDAYS

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
ARCHIV_DIR = SITE_DIR / "archiv"

# Reihenfolge innerhalb eines Tages: catchup < morgen < abend
_EDITION_RANK = {"catchup": 0, "morgen": 1, "abend": 2}
_EDITION_LABEL = {"morgen": "Morgen", "abend": "Abend", "catchup": "Catch-up"}
_FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(morgen|abend|catchup)\.html$")

NOINDEX = '<meta name="robots" content="noindex">'

_NAV_TEMPLATE = """  <hr>
  <div style="font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
              font-size: 14px; color: #6b6458;">
    <div style="letter-spacing: 0.14em; text-transform: uppercase; font-size: 12px;
                margin-bottom: 10px;">Archiv</div>
{items}
  </div>
"""


def _parse(path: Path) -> tuple[date, int, str] | None:
    """Liest (Datum, Tagesrang, Edition) aus dem Dateinamen, sonst None."""
    m = _FILENAME_RE.match(path.name)
    if not m:
        return None
    try:
        d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None
    edition = m.group(4)
    return d, _EDITION_RANK[edition], edition


def _label(d: date, edition: str) -> str:
    return f"{WEEKDAYS[d.weekday()]} {d.day}. {MONTHS[d.month - 1]} · {_EDITION_LABEL[edition]}"


def build_site() -> Path:
    """Kopiert neue Ausgaben ins Archiv und baut site/index.html neu."""
    ARCHIV_DIR.mkdir(parents=True, exist_ok=True)
    if OUT_DIR.exists():
        for path in OUT_DIR.glob("*.html"):
            if _parse(path):
                shutil.copy2(path, ARCHIV_DIR / path.name)

    editions = [
        (parsed, path)
        for path in ARCHIV_DIR.glob("*.html")
        if (parsed := _parse(path))
    ]
    index = SITE_DIR / "index.html"
    if not editions:
        print("Keine Ausgaben im Archiv — index.html bleibt unverändert.")
        return index

    # Neueste Ausgabe per Dateiname bestimmen, nicht per mtime (nach einem
    # frischen Checkout tragen alle Dateien denselben Zeitstempel).
    editions.sort(key=lambda e: e[0], reverse=True)
    latest_path = editions[0][1]

    html = latest_path.read_text(encoding="utf-8")
    if NOINDEX not in html:
        html = html.replace("<head>", f"<head>\n{NOINDEX}", 1)

    items = "\n".join(
        f'    <p style="margin: 0 0 6px;">'
        f'<a href="archiv/{path.name}" style="color: #6b6458;">{_label(d, edition)}</a></p>'
        for (d, _rank, edition), path in editions[:14]
    )
    nav = _NAV_TEMPLATE.format(items=items)
    html = html.replace("</div>\n</body>", f"{nav}</div>\n</body>", 1)

    index.write_text(html, encoding="utf-8")
    print(f"Web-Ansicht gebaut: {index} ({len(editions)} Ausgabe(n) im Archiv)")
    return index
