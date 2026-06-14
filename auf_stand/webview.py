"""Baut die statische Web-App (site/) aus den erzeugten Lagebildern."""
from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path

from .render import OUT_DIR
from .vorausschau import MONTHS, WEEKDAYS

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
ARCHIV_DIR = SITE_DIR / "archiv"
STATE_PATH = BASE_DIR / "data" / "state.json"

_EDITION_RANK = {"catchup": 0, "morgen": 1, "abend": 2}
_EDITION_LABEL = {"morgen": "Morgen-Ausgabe", "abend": "Abend-Ausgabe", "catchup": "Catch-up"}
_FILENAME_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(morgen|abend|catchup)\.html$")

# ---------------------------------------------------------------------------
# Design-System — Die Presse · Auf Stand (Dark, im Look der echten App)
# Platzhalter: __TITLE__  __ROOT__  __NAV_LAGEBILD__  __NAV_DOSSIER__
#              __NAV_ARCHIV__  __CONTENT__
# ---------------------------------------------------------------------------
_ICON_HOME = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
              'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
              '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>')
_ICON_DOSSIER = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                 'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
                 '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/></svg>')
_ICON_ARCHIV = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M12 4 3 8l9 4 9-4-9-4z"/><path d="M3 12l9 4 9-4"/>'
                '<path d="M3 16l9 4 9-4"/></svg>')
_ICON_EPAPER = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
                '<path d="M4 5h12v14H6a2 2 0 0 1-2-2V5z"/>'
                '<path d="M16 8h4v9a2 2 0 0 1-2 2"/>'
                '<path d="M7 8h6M7 11h6M7 14h4"/></svg>')

_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="robots" content="noindex">
  <meta name="theme-color" content="#0d0d0d">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=GFS+Didot&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
  <title>__TITLE__ · Die Presse · Auf Stand</title>
  <style>
    /* Die-Presse-Design-System — Farben in oklch (visual hierarchy ∝ 1/L).
       Akzent: Navy-Blau der „Interview"-Box. */
    :root { --bg: oklch(0.16 0 0); --surface: oklch(0.21 0 0);
            --border: oklch(0.31 0 0); --text: oklch(0.97 0 0);
            --muted: oklch(0.72 0 0); --accent: oklch(0.40 0.07 256);
            --accent-bright: oklch(0.72 0.12 252);
            --serif: 'GFS Didot', 'Playfair Display', Georgia, 'Times New Roman', serif;
            --sans: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: Georgia, serif;
           font-size: 17px; line-height: 1.6; padding-bottom: 76px;
           -webkit-font-smoothing: antialiased; }
    a { color: var(--accent-bright); text-decoration: none; }
    a:hover { text-decoration: underline; }
    /* ── Masthead ── */
    .masthead { text-align: center; padding: 30px 20px 18px;
                border-bottom: 2px solid var(--accent); }
    .wordmark { font-family: var(--serif); font-weight: 400; font-size: 40px;
                letter-spacing: -0.01em; color: var(--text); line-height: 1; }
    .sublabel { font-family: var(--sans); font-size: 10px; letter-spacing: 0.42em;
                text-transform: uppercase; color: var(--muted); margin-top: 12px;
                font-weight: 600; padding-left: 0.42em; }
    /* ── Layout ── */
    .wrap { max-width: 720px; margin: 0 auto; padding: 34px 20px 48px; }
    /* ── Typografie (Serifen-Skala) ── */
    h1 { font-family: var(--serif); font-size: 2.4rem; line-height: 1.14;
         margin: 0 0 14px; font-weight: 400; color: var(--text);
         letter-spacing: -0.01em; }
    h2 { font-family: var(--serif); font-size: 1.55rem; line-height: 1.22;
         margin: 40px 0 12px; font-weight: 700; color: var(--text); }
    p { margin: 0 0 14px; color: oklch(0.92 0 0); }
    strong { font-family: var(--sans); font-size: 11.5px; letter-spacing: 0.07em;
             text-transform: uppercase; color: var(--accent-bright); font-weight: 700; }
    em { font-style: italic; color: var(--muted); }
    hr { border: none; border-top: 1px solid var(--border); margin: 30px 0; }
    /* ── Heute-wichtig-Box ── */
    .highlights { background: var(--surface); border-left: 3px solid var(--accent);
                  border-radius: 8px; padding: 16px 18px; margin: 4px 0 26px; }
    .highlights p { margin: 0 0 8px; font-size: 16px; }
    .highlights p:last-child { margin-bottom: 0; }
    .highlights strong { display: block; margin-bottom: 8px; }
    /* ── Ressort-Tag (farbig, oklch via --h) ── */
    .ressort { display: inline-block; background: oklch(0.30 0.06 var(--h, 24));
               color: oklch(0.86 0.13 var(--h, 24)); border-radius: 999px;
               padding: 3px 11px; font-family: var(--sans); font-size: 11px;
               font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
               vertical-align: middle; }
    /* ── Quell-Link als rote Primary-Pill ── */
    .source-link { display: inline-block; margin-top: 4px; background: var(--accent);
                   color: var(--text); border-radius: 999px; padding: 5px 15px;
                   font-family: var(--sans); font-size: 12px; font-weight: 600;
                   letter-spacing: 0.04em; text-decoration: none; }
    .source-link:hover { background: oklch(0.49 0.09 256); color: var(--text);
                         text-decoration: none; }
    /* ── Status / Done box ── */
    .done { border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px;
            background: var(--surface); color: oklch(0.78 0.15 150);
            font-family: var(--sans); font-size: 14px; margin: 32px 0; }
    /* ── Archiv-Karten ── */
    .archiv-grid { display: grid;
                   grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                   gap: 12px; margin-top: 28px; }
    .archiv-card { display: block; border: 1px solid var(--border); border-radius: 10px;
                   padding: 16px 18px; background: var(--surface); }
    .archiv-card:hover { border-color: var(--accent); text-decoration: none; }
    .archiv-date { display: block; font-family: -apple-system, 'Segoe UI', sans-serif;
                   font-size: 13px; color: var(--text); font-weight: 600; margin-bottom: 4px; }
    .archiv-label { display: block; font-family: -apple-system, 'Segoe UI', sans-serif;
                    font-size: 12px; color: var(--muted); }
    /* ── Dossier / Themen-Verlauf ── */
    .dossier-topic { margin: 0 0 40px; }
    .dossier-topic h2 { border-bottom: 1px solid var(--border); padding-bottom: 8px;
                        margin-bottom: 16px; }
    .dossier-entries { list-style: none; padding: 0; margin: 0; }
    .dossier-entries li { padding: 10px 0; border-bottom: 1px solid var(--border);
                           display: flex; gap: 14px; align-items: baseline; font-size: 16px;
                           color: oklch(0.92 0 0); }
    .dossier-entries li:last-child { border-bottom: none; }
    .dossier-date { font-family: -apple-system, 'Segoe UI', sans-serif; font-size: 12px;
                    color: var(--accent); font-weight: 600; white-space: nowrap; min-width: 72px; }
    .empty-state { color: var(--muted); font-style: italic; padding: 40px 0; text-align: center;
                   font-family: -apple-system, 'Segoe UI', sans-serif; font-size: 15px; }
    /* ── Tab-Leiste unten ── */
    .tabbar { position: fixed; bottom: 0; left: 0; right: 0; height: 64px;
              background: var(--surface); border-top: 1px solid var(--border);
              display: flex; z-index: 10; }
    .tab { flex: 1; display: flex; flex-direction: column; align-items: center;
           justify-content: center; gap: 3px; color: var(--muted);
           font-family: -apple-system, 'Segoe UI', sans-serif; font-size: 10px;
           letter-spacing: 0.04em; text-transform: uppercase; border-top: 2px solid transparent; }
    .tab:hover { color: var(--text); text-decoration: none; }
    .tab svg { width: 23px; height: 23px; }
    .tab.active { color: var(--text); border-top-color: var(--accent); }
    /* ── Artikel-Feedback ── */
    .article-fb { display: flex; gap: 8px; margin: 14px 0 4px; }
    .fb-btn { background: none; border: 1px solid var(--border); border-radius: 999px;
              padding: 5px 14px; font-size: 13px; cursor: pointer; color: var(--muted);
              font-family: var(--sans); line-height: 1; }
    .fb-btn.active[data-vote="up"] { background: oklch(0.22 0.06 150);
              border-color: oklch(0.50 0.15 150); color: oklch(0.75 0.15 150); }
    .fb-btn.active[data-vote="down"] { background: oklch(0.22 0.04 24);
              border-color: oklch(0.42 0.10 24); color: oklch(0.68 0.10 24); }
  </style>
</head>
<body>
<header class="masthead">
  <div class="wordmark">Die Presse</div>
  <div class="sublabel">Auf Stand</div>
</header>
<div class="wrap">
__CONTENT__
</div>
<nav class="tabbar">
  <a href="__ROOT__index.html" class="tab __NAV_LAGEBILD__">__ICON_HOME__<span>Lagebild</span></a>
  <a href="__ROOT__dossier.html" class="tab __NAV_DOSSIER__">__ICON_DOSSIER__<span>Themen</span></a>
  <a href="__ROOT__archiv/index.html" class="tab __NAV_ARCHIV__">__ICON_ARCHIV__<span>Archiv</span></a>
  <a href="https://www.diepresse.com/epaper" class="tab" target="_blank" rel="noopener">__ICON_EPAPER__<span>E-Paper</span></a>
</nav>
<script>
(function(){
  function castVote(btn){
    var bar=btn.closest('.article-fb');
    var key='afb_'+bar.dataset.key;
    var vote=btn.dataset.vote;
    var prev=localStorage.getItem(key);
    bar.querySelectorAll('.fb-btn').forEach(function(b){b.classList.remove('active');});
    if(prev!==vote){localStorage.setItem(key,vote);btn.classList.add('active');}
    else{localStorage.removeItem(key);}
  }
  document.querySelectorAll('.article-fb').forEach(function(bar){
    var saved=localStorage.getItem('afb_'+bar.dataset.key);
    if(saved){var b=bar.querySelector('[data-vote="'+saved+'"]');if(b)b.classList.add('active');}
    bar.querySelectorAll('.fb-btn').forEach(function(btn){
      btn.addEventListener('click',function(){castVote(btn);});
    });
  });
})();
</script>
</body>
</html>
"""


def _render_page(title: str, content: str, active: str, root: str = "") -> str:
    """Füllt das Page-Template mit Inhalt und aktivem Tab."""
    nav = {"lagebild": "", "dossier": "", "archiv": ""}
    if active in nav:
        nav[active] = "active"
    return (
        _PAGE_TEMPLATE
        .replace("__TITLE__", title)
        .replace("__ROOT__", root)
        .replace("__NAV_LAGEBILD__", nav["lagebild"])
        .replace("__NAV_DOSSIER__", nav["dossier"])
        .replace("__NAV_ARCHIV__", nav["archiv"])
        .replace("__ICON_HOME__", _ICON_HOME)
        .replace("__ICON_DOSSIER__", _ICON_DOSSIER)
        .replace("__ICON_ARCHIV__", _ICON_ARCHIV)
        .replace("__ICON_EPAPER__", _ICON_EPAPER)
        .replace("__CONTENT__", content)
    )


# Ressort → oklch-Hue-Winkel (farbcodierte Tags wie im Die-Presse-Design-System).
_RESSORT_HUE = {
    "politik": 245, "wirtschaft": 175, "unternehmen": 175, "börse": 175,
    "international": 265, "ausland": 265, "europa": 265,
    "recht": 35, "justiz": 35, "energie": 75, "umwelt": 130,
    "wissenschaft": 150, "tech": 150, "technik": 150, "digital": 150,
    "wien": 25, "lokales": 25, "chronik": 25, "sport": 200, "kultur": 300,
}


def _ressort_tag(match: re.Match) -> str:
    name = match.group(1).strip()
    hue = _RESSORT_HUE.get(name.split("/")[0].split()[0].lower(), 24)
    return f' <span class="ressort" style="--h:{hue}">{name}</span>'


def _add_article_feedback(content: str, datum: str, edition: str) -> str:
    """Fügt 👍/👎-Buttons nach jedem nummerierten Artikel (vor dem <hr>) ein."""
    if 'class="article-fb"' in content:
        return content
    blocks = content.split("<hr>")
    result = []
    idx = 0
    for block in blocks:
        if re.search(r"<h2>[1-9]", block):
            key = f"{datum}|{edition}|{idx}"
            block = block.rstrip() + (
                f'\n<div class="article-fb" data-key="{key}">'
                f'<button class="fb-btn" data-vote="up">👍 Relevant</button>'
                f'<button class="fb-btn" data-vote="down">👎</button>'
                f"</div>"
            )
            idx += 1
        result.append(block)
    return "<hr>".join(result)


def _enhance_content(content: str, datum: str = "", edition: str = "") -> str:
    """Verleiht dem Roh-Inhalt Die-Presse-Charakter (Pills, Kicker, Highlight-Box)."""
    # Marken-Zeile entfernen (steht jetzt im Masthead) — als <p> oder <div>.
    content = re.sub(
        r'<(p|div)[^>]*class="brand"[^>]*>.*?</\1>\s*', "", content, flags=re.DOTALL
    )
    # Ressort am Punkt-Ende „… </a> (Politik)" → farbiger Tag (vor Link-Umbau).
    if 'class="ressort"' not in content:
        content = re.sub(r'</a>\s*\(([^)]{2,30})\)', lambda m: "</a>" + _ressort_tag(m), content)
    # Quell-Links als rote Primary-Pill auszeichnen.
    content = re.sub(
        r'<a href="([^"]+)">→ Artikel</a>',
        r'<a class="source-link" href="\1">Weiterlesen bei der Presse →</a>',
        content,
    )
    # „Heute wichtig" + die nummerierten Zeilen zu einer Highlight-Box bündeln.
    # Nur einmal — beim erneuten Rendern ist die Box schon vorhanden.
    if 'class="highlights"' not in content:
        content = re.sub(
            r'(<p><strong>Heute wichtig:</strong></p>.*?)(?=<hr>)',
            r'<div class="highlights">\1</div>',
            content,
            count=1,
            flags=re.DOTALL,
        )
    if datum:
        content = _add_article_feedback(content, datum, edition)
    return content.strip()


def _extract_body(html: str, datum: str = "", edition: str = "") -> str:
    """Extrahiert Inhalt der .wrap-Div — korrekt bei verschachtelten Divs."""
    marker = '<div class="wrap">'
    start = html.find(marker)
    if start == -1:
        return "<p>Kein Inhalt verfügbar.</p>"
    content_start = start + len(marker)
    depth = 1
    i = content_start
    while i < len(html) and depth > 0:
        o = html.find("<div", i)
        c = html.find("</div>", i)
        if c == -1:
            break
        if o != -1 and o < c:
            depth += 1
            i = o + 4
        else:
            depth -= 1
            if depth == 0:
                return _enhance_content(html[content_start:c].strip(), datum, edition)
            i = c + 6
    return "<p>Kein Inhalt verfügbar.</p>"


def _parse(path: Path) -> tuple[date, int, str] | None:
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


def _iso_to_display(iso: str) -> str:
    try:
        return f"{iso[8:10]}.{iso[5:7]}.{iso[:4]}"
    except (IndexError, TypeError):
        return iso


# ---------------------------------------------------------------------------
# Seiten-Generatoren
# ---------------------------------------------------------------------------

def build_dossier(dossier: dict) -> None:
    """Erzeugt site/dossier.html mit Die Presse-Design."""
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    sections: list[str] = []
    for topic_name, entries in dossier.items():
        if not entries:
            continue
        sorted_entries = sorted(entries, key=lambda e: e.get("date", ""), reverse=True)
        items = "\n".join(
            f'<li><span class="dossier-date">{_iso_to_display(e["date"])}</span>'
            f"<span>{e['summary']}</span></li>"
            for e in sorted_entries
            if e.get("summary")
        )
        sections.append(
            f'<div class="dossier-topic">'
            f"<h2>{topic_name}</h2>"
            f'<ul class="dossier-entries">{items}</ul>'
            f"</div>"
        )

    if sections:
        body = "\n".join(sections)
    else:
        body = '<p class="empty-state">Noch kein Verlauf — erscheint nach der nächsten Ausgabe.</p>'

    content = f"<h1>Themen-Verlauf</h1>\n{body}"
    html = _render_page("Themen-Verlauf", content, "dossier")
    (SITE_DIR / "dossier.html").write_text(html, encoding="utf-8")


def build_archiv_index(editions: list) -> None:
    """Erzeugt site/archiv/index.html als Karten-Raster."""
    ARCHIV_DIR.mkdir(parents=True, exist_ok=True)
    cards = "\n".join(
        f'<a class="archiv-card" href="{path.name}">'
        f'<span class="archiv-date">{_label(d, edition)}</span>'
        f'<span class="archiv-label">{_EDITION_LABEL[edition]}</span>'
        f"</a>"
        for (d, _rank, edition), path in editions[:60]
    )
    content = f'<h1>Archiv</h1>\n<div class="archiv-grid">\n{cards}\n</div>'
    html = _render_page("Archiv", content, "archiv", root="../")
    (ARCHIV_DIR / "index.html").write_text(html, encoding="utf-8")


def build_site() -> Path:
    """Kopiert neue Ausgaben ins Archiv und baut alle Site-Seiten neu."""
    state: dict = {}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    build_dossier(state.get("dossier", {}))

    ARCHIV_DIR.mkdir(parents=True, exist_ok=True)
    fresh_copies: set[str] = set()
    if OUT_DIR.exists():
        for path in OUT_DIR.glob("*.html"):
            if _parse(path):
                shutil.copy2(path, ARCHIV_DIR / path.name)
                fresh_copies.add(path.name)

    editions = [
        (parsed, path)
        for path in ARCHIV_DIR.glob("*.html")
        if (parsed := _parse(path))
    ]
    index = SITE_DIR / "index.html"
    if not editions:
        print("Keine Ausgaben im Archiv — index.html bleibt unverändert.")
        return index

    editions.sort(key=lambda e: e[0], reverse=True)

    # Archiv-Einzelseiten: frisch kopierte neu templateisieren,
    # bereits gebrandete (aus git) nur wenn sie das aktuelle Dark-Template
    # noch nicht haben (erkennbar an der Tab-Leiste).
    for (d, _rank, edition), path in editions:
        raw = path.read_text(encoding="utf-8")
        if path.name in fresh_copies or 'class="tabbar"' not in raw:
            content = _extract_body(raw, d.isoformat(), edition)
            branded = _render_page(_label(d, edition), content, "archiv", root="../")
            path.write_text(branded, encoding="utf-8")

    build_archiv_index(editions)

    # Hauptseite: neueste Ausgabe
    latest_html = editions[0][1].read_text(encoding="utf-8")
    latest_d, _, latest_edition = editions[0][0]
    latest_content = _extract_body(latest_html, latest_d.isoformat(), latest_edition)
    title = _label(latest_d, latest_edition)
    index_html = _render_page(title, latest_content, "lagebild")
    index.write_text(index_html, encoding="utf-8")

    print(f"Web-App gebaut: {index} ({len(editions)} Ausgabe(n) im Archiv)")
    return index
