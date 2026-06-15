"""Baut die statische Web-App (site/) aus den erzeugten Lagebildern."""
from __future__ import annotations

import html as _html
import json
import re
import shutil
from datetime import date
from pathlib import Path

import yaml

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
  <meta name="theme-color" content="#ffffff">
  <link rel="manifest" href="__ROOT__manifest.webmanifest">
  <link rel="icon" href="__ROOT__favicon-32.png" sizes="32x32" type="image/png">
  <link rel="apple-touch-icon" href="__ROOT__apple-touch-icon.png">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="Auf Stand">
  <meta name="application-name" content="Auf Stand">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Libre+Caslon+Text:ital,wght@0,400;0,700;1,400&family=Libre+Franklin:wght@400;500;600;700&display=swap" rel="stylesheet">
  <title>__TITLE__ · Die Presse · Auf Stand</title>
  <style>
    /* Auf Stand — helles, ruhiges Redaktions-Layout im Geist der New York Times:
       Schwarz auf Weiß, viel Weißraum, ein einziger zurückhaltender Akzent (Link-Blau).
       Schriften: Libre Caslon Text (Headlines), Libre Franklin (UI), Georgia (Fließtext). */
    :root { --bg: #ffffff; --surface: #f7f6f3;
            --border: #e3e1dc; --text: #121212; --fg: #121212;
            --muted: #6b6b6b; --accent: #326891;
            --accent-bright: #326891;
            --serif: 'Libre Caslon Text', Georgia, 'Times New Roman', serif;
            --sans: 'Libre Franklin', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif; }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: Georgia, serif;
           font-size: 18px; line-height: 1.65; padding-bottom: 76px;
           -webkit-font-smoothing: antialiased; }
    a { color: var(--accent-bright); text-decoration: none; }
    a:hover { text-decoration: underline; }
    /* ── Masthead ── */
    .masthead { text-align: center; padding: 34px 20px 20px;
                border-bottom: 1px solid var(--text); }
    .wordmark { font-family: var(--serif); font-weight: 400; font-size: 38px;
                letter-spacing: 0.01em; color: var(--text); line-height: 1; }
    .sublabel { font-family: var(--sans); font-size: 10px; letter-spacing: 0.42em;
                text-transform: uppercase; color: var(--muted); margin-top: 12px;
                font-weight: 600; padding-left: 0.42em; }
    /* ── Layout ── */
    .wrap { max-width: 680px; margin: 0 auto; padding: 38px 20px 56px; }
    /* ── Typografie (Serifen-Skala) ── */
    h1 { font-family: var(--serif); font-size: 2.5rem; line-height: 1.16;
         margin: 0 0 14px; font-weight: 400; color: var(--text);
         letter-spacing: -0.005em; }
    h2 { font-family: var(--serif); font-size: 1.55rem; line-height: 1.25;
         margin: 44px 0 12px; font-weight: 700; color: var(--text); }
    p { margin: 0 0 15px; color: #1f1f1f; }
    strong { font-family: var(--sans); font-size: 11.5px; letter-spacing: 0.07em;
             text-transform: uppercase; color: var(--accent); font-weight: 700; }
    em { font-style: italic; color: var(--muted); }
    hr { border: none; border-top: 1px solid var(--border); margin: 34px 0; }
    /* ── Byline (redaktionelle Stimme) ── */
    .byline { font-family: var(--sans); font-size: 13px; color: var(--muted);
              font-weight: 500; letter-spacing: 0.01em; margin: 0 0 24px;
              padding-bottom: 16px; border-bottom: 1px solid var(--border);
              text-transform: none; }
    /* ── Streak-Ritus (nur Startseite) ── */
    .streak { display: inline-flex; align-items: center; gap: 7px;
              font-family: var(--sans); font-size: 13px; font-weight: 600;
              color: var(--accent); background: #eef3f8; border: 1px solid #d4e1ee;
              border-radius: 999px; padding: 7px 15px; margin: 0 0 22px; }
    /* ── Heute-wichtig-Box ── */
    .highlights { background: var(--surface); border-left: 3px solid var(--accent);
                  border-radius: 8px; padding: 16px 18px; margin: 4px 0 26px; }
    .highlights p { margin: 0 0 8px; font-size: 16px; }
    .highlights p:last-child { margin-bottom: 0; }
    .highlights strong { display: block; margin-bottom: 8px; }
    /* ── Ressort-Tag (farbig, oklch via --h — helle Variante) ── */
    .ressort { display: inline-block; background: oklch(0.95 0.03 var(--h, 24));
               color: oklch(0.45 0.13 var(--h, 24)); border-radius: 999px;
               padding: 3px 11px; font-family: var(--sans); font-size: 11px;
               font-weight: 600; letter-spacing: 0.06em; text-transform: uppercase;
               vertical-align: middle; }
    /* ── Quell-Link als Primary-Pill ── */
    .source-link { display: inline-block; margin-top: 4px; background: var(--accent);
                   color: #ffffff; border-radius: 999px; padding: 5px 15px;
                   font-family: var(--sans); font-size: 12px; font-weight: 600;
                   letter-spacing: 0.04em; text-decoration: none; }
    .source-link:hover { background: #284f6f; color: #ffffff;
                         text-decoration: none; }
    /* ── Status / Done box ── */
    .done { border: 1px solid #cfe3d3; border-radius: 10px; padding: 14px 18px;
            background: #f0f7f1; color: #2e6b3f;
            font-family: var(--sans); font-size: 14px; margin: 32px 0; }
    /* ── Archiv-Karten ── */
    .archiv-grid { display: grid;
                   grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
                   gap: 12px; margin-top: 28px; }
    .archiv-card { display: block; border: 1px solid var(--border); border-radius: 10px;
                   padding: 16px 18px; background: var(--surface); }
    .archiv-card:hover { border-color: var(--accent); text-decoration: none; }
    .archiv-date { display: block; font-family: var(--sans);
                   font-size: 13px; color: var(--text); font-weight: 600; margin-bottom: 4px; }
    .archiv-label { display: block; font-family: var(--sans);
                    font-size: 12px; color: var(--muted); }
    /* ── Dossier / Themen-Verlauf ── */
    .dossier-topic { margin: 0 0 40px; }
    .dossier-topic h2 { border-bottom: 1px solid var(--border); padding-bottom: 8px;
                        margin-bottom: 16px; }
    .dossier-entries { list-style: none; padding: 0; margin: 0; }
    .dossier-entries li { padding: 10px 0; border-bottom: 1px solid var(--border);
                           display: flex; gap: 14px; align-items: baseline; font-size: 16px;
                           color: #1f1f1f; }
    .dossier-entries li:last-child { border-bottom: none; }
    .dossier-date { font-family: var(--sans); font-size: 12px;
                    color: var(--accent); font-weight: 600; white-space: nowrap; min-width: 72px; }
    .empty-state { color: var(--muted); font-style: italic; padding: 40px 0; text-align: center;
                   font-family: var(--sans); font-size: 15px; }
    /* ── Tab-Leiste unten ── */
    .tabbar { position: fixed; bottom: 0; left: 0; right: 0; height: 64px;
              background: #ffffff; border-top: 1px solid var(--border);
              display: flex; z-index: 10; }
    .tab { flex: 1; display: flex; flex-direction: column; align-items: center;
           justify-content: center; gap: 3px; color: var(--muted);
           font-family: var(--sans); font-size: 10px;
           letter-spacing: 0.04em; text-transform: uppercase; border-top: 2px solid transparent; }
    .tab:hover { color: var(--text); text-decoration: none; }
    .tab svg { width: 23px; height: 23px; }
    .tab.active { color: var(--text); border-top-color: var(--accent); }
    /* ── Artikel-Feedback ── */
    .article-fb { display: flex; gap: 8px; margin: 14px 0 4px; }
    .fb-btn { background: none; border: 1px solid var(--border); border-radius: 999px;
              padding: 5px 14px; font-size: 13px; cursor: pointer; color: var(--muted);
              font-family: var(--sans); line-height: 1; }
    .fb-btn.active[data-vote="up"] { background: #eaf5ec;
              border-color: #9ccfa5; color: #2e6b3f; }
    .fb-btn.active[data-vote="down"] { background: #fdeceb;
              border-color: #e3a9a4; color: #b3261e; }
    /* ── Themen-Reiter ── */
    .schlagwort-badge { display: inline-block; font-size: 11px; font-family: var(--sans);
                        color: var(--accent); background: #eef3f8;
                        border: 1px solid #d4e1ee; border-radius: 999px;
                        padding: 2px 8px; margin-left: 8px; vertical-align: middle;
                        letter-spacing: 0.03em; }
    .dossier-empty { color: var(--muted); font-style: italic; font-size: 14px;
                     font-family: var(--sans); padding: 10px 0 6px; }
    .topic-stand { font-size: 13px; color: var(--muted); font-style: italic;
                   font-family: var(--sans); margin: 6px 0 10px; }
    .topic-articles { list-style: none; padding: 0; margin: 0; }
    .topic-article { padding: 10px 0; border-bottom: 1px solid var(--border); }
    .topic-article:last-child { border-bottom: none; }
    .topic-article a { color: var(--fg); text-decoration: none; display: flex;
                        justify-content: space-between; align-items: baseline; gap: 10px; }
    .topic-article-title { flex: 1; font-size: 15px; line-height: 1.4; }
    .topic-article-date { font-size: 12px; color: var(--muted);
                           font-family: var(--sans); white-space: nowrap; }
    /* ── Assessment v2 (Toggle-Karten) ── */
    .as-intro-text { font-size: 15px; color: var(--muted); font-family: var(--sans);
                     line-height: 1.6; margin-bottom: 20px; }
    .as-btn-primary { background: var(--accent); border-color: var(--accent);
                       color: #ffffff; font-weight: 600; border-radius: 999px;
                       padding: 13px 28px; font-size: 15px; cursor: pointer;
                       font-family: var(--sans); border: none; display: inline-block; }
    .as-toggle-card { display: flex; gap: 14px; align-items: flex-start;
                       padding: 14px; border: 1px solid var(--border); border-radius: 10px;
                       margin: 8px 0; cursor: pointer; transition: border-color 0.15s,background 0.15s;
                       user-select: none; }
    .as-toggle-card.selected { border-color: var(--accent); background: #eef3f8; }
    .as-card-check { width: 22px; height: 22px; border-radius: 50%;
                      border: 1.5px solid var(--border); display: flex; align-items: center;
                      justify-content: center; flex-shrink: 0; font-size: 12px;
                      color: transparent; margin-top: 1px; transition: all 0.15s; }
    .as-toggle-card.selected .as-card-check { background: var(--accent);
      border-color: var(--accent); color: #ffffff; }
    .as-card-name { font-size: 15px; font-weight: 600; margin-bottom: 3px; line-height: 1.3; }
    .as-card-q { font-size: 13px; color: var(--muted); font-family: var(--sans); line-height: 1.4; }
    .as-custom-section { border-top: 1px solid var(--border); padding-top: 20px; margin-top: 12px; }
    .as-custom-inputs { display: flex; gap: 8px; margin: 10px 0 12px; flex-wrap: wrap; }
    .as-custom-input { flex: 1; min-width: 130px; background: #ffffff;
                        border: 1px solid var(--border); border-radius: 8px;
                        padding: 10px 12px; color: var(--fg); font-size: 14px;
                        font-family: var(--sans); outline: none; }
    .as-custom-input:focus { border-color: var(--accent); }
    .as-add-btn { background: none; border: 1px solid var(--border); border-radius: 999px;
                   padding: 10px 18px; color: var(--fg); font-size: 14px;
                   cursor: pointer; font-family: var(--sans); white-space: nowrap; }
    .as-add-btn:hover { border-color: var(--accent); }
    .as-confirm-row { display: flex; justify-content: space-between; align-items: center;
                       margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border); }
    .as-cmd-box { background: var(--surface); border: 1px solid var(--border);
                   border-radius: 8px; padding: 14px; margin: 10px 0 16px;
                   font-family: monospace; font-size: 13px; color: var(--accent);
                   white-space: pre-wrap; line-height: 1.7; }
    .tg-copy-btn { background: none; border: 1px solid var(--border); border-radius: 6px;
                   padding: 5px 12px; font-size: 12px; color: var(--muted);
                   cursor: pointer; font-family: var(--sans); margin-left: 8px; }
    .reset-link { font-size: 12px; color: var(--muted); font-family: var(--sans);
                  text-decoration: underline; cursor: pointer; margin-top: 24px;
                  display: inline-block; background: none; border: none; padding: 0; }
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
  // PWA: Service Worker registrieren (Offline-Cache, „Auf Home Screen").
  if('serviceWorker' in navigator){
    window.addEventListener('load',function(){
      navigator.serviceWorker.register('__ROOT__sw.js').catch(function(){});
    });
  }
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
    """Fügt 👍/👎-Buttons nach jedem nummerierten Artikel ein."""
    content = re.sub(r'\n?<div class="article-fb".*?</div>', "", content)
    idx = 0

    def _insert(m: re.Match) -> str:
        nonlocal idx
        key = f"{datum}|{edition}|{idx}"
        idx += 1
        bar = (
            f'\n<div class="article-fb" data-key="{key}">'
            f'<button class="fb-btn" data-vote="up">👍 Relevant</button>'
            f'<button class="fb-btn" data-vote="down">👎</button>'
            f"</div>"
        )
        return m.group(0).rstrip() + bar

    # Jeder Artikel reicht von <h2>[Ziffer] bis zum nächsten <h2>[Ziffer] oder <hr>
    return re.sub(r"<h2>[1-9].*?(?=<h2>[1-9]|<hr>)", _insert, content, flags=re.DOTALL)


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
    # Redaktionelle Byline direkt unter die H1 — deterministisch, damit sie nie fehlt.
    if 'class="byline"' not in content:
        content = re.sub(
            r"(</h1>)",
            r'\1\n<p class="byline">Von der Auf-Stand-Redaktion</p>',
            content,
            count=1,
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

def _topic_card_html(topic, dossier: dict, topic_articles: dict) -> str:
    """HTML für eine einzelne Topic-Karte (nach abgeschlossenem Assessment)."""
    from .synthesize import topic_keyword, topic_name as get_topic_name
    name = get_topic_name(topic)
    kw = topic_keyword(topic)
    badge = f'<span class="schlagwort-badge">#{kw}</span>' if kw else ""
    dossier_entries = sorted(
        dossier.get(name, []), key=lambda e: e.get("date", ""), reverse=True
    )
    stand_html = ""
    if dossier_entries and dossier_entries[0].get("summary"):
        stand_html = f'<p class="topic-stand">Stand: {dossier_entries[0]["summary"]}</p>'
    arts = topic_articles.get(name, [])
    if arts:
        items = "\n".join(
            f'<li class="topic-article">'
            f'<a href="{a["link"]}" target="_blank" rel="noopener">'
            f'<span class="topic-article-title">{a["title"]}</span>'
            f'<span class="topic-article-date">{_iso_to_display(a["date"])[:5]}</span>'
            f"</a></li>"
            for a in arts
            if a.get("link") and a.get("title")
        )
        body_html = f'<ul class="topic-articles">{items}</ul>'
    else:
        body_html = '<p class="dossier-empty">Keine aktuellen Artikel zu diesem Thema.</p>'
    return (
        f'<div class="dossier-topic" data-topic-name="{_html.escape(name)}">'
        f"<h2>{_html.escape(name)}{badge}</h2>"
        f"{stand_html}{body_html}"
        f"</div>"
    )


def build_dossier(
    dossier: dict,
    topics: list,
    topic_articles: dict,
    assessment_questions: list | None = None,
) -> None:
    """Erzeugt site/dossier.html mit Toggle-Karten-Assessment und Topic-Karten."""
    from .synthesize import topic_keyword, topic_name as get_topic_name
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    # Topic-Karten (nach Assessment)
    topic_cards = "\n".join(_topic_card_html(t, dossier, topic_articles) for t in topics)
    if not topic_cards:
        topic_cards = '<p class="empty-state">Keine Themen konfiguriert.</p>'

    # Fragen-Mapping: bevorzuge dynamische (artikel-basierte) Fragen, Fallback auf statische
    dyn_q = {q["name"]: q["question"] for q in (assessment_questions or [])}
    topics_data = [
        {
            "name": get_topic_name(t),
            "kw": topic_keyword(t),
            "q": dyn_q.get(get_topic_name(t)) or (
                t.get("assessment_question", "") if isinstance(t, dict) else ""
            ),
        }
        for t in topics
        if isinstance(t, dict) and (t.get("assessment_question") or dyn_q.get(get_topic_name(t)))
    ]
    topics_js = json.dumps(topics_data, ensure_ascii=False)

    # Toggle-Karten für das Assessment (eine pro Topic)
    toggle_cards_html = "\n".join(
        f'<div class="as-toggle-card" data-name="{_html.escape(td["name"])}" onclick="asToggle(this)">'
        f'<div class="as-card-check">✓</div>'
        f'<div><div class="as-card-name">{_html.escape(td["name"])}</div>'
        f'<div class="as-card-q">{_html.escape(td["q"])}</div></div>'
        f"</div>"
        for td in topics_data
    )

    assessment_html = f"""
<div id="as-intro">
  <p class="as-intro-text">Wähle die Themen aus, über die du regelmäßig auf Stand gehalten werden möchtest. Die Fragen helfen dir einzuschätzen, was für dich relevant ist.</p>
  <button class="as-btn-primary" onclick="asOpen()">Themen auswählen →</button>
</div>

<div id="as-cards" style="display:none">
  <p style="font-size:13px;color:var(--muted);font-family:var(--sans);margin:0 0 16px">
    Tippe auf ein Thema, um es auszuwählen oder abzuwählen.
  </p>
  {toggle_cards_html}

  <div class="as-custom-section">
    <p style="font-size:14px;font-family:var(--sans);margin:0 0 4px;font-weight:600">Eigenes Thema hinzufügen</p>
    <p style="font-size:13px;color:var(--muted);font-family:var(--sans);margin:0 0 10px">Trage ein Thema und ein kurzes Erkennungswort ein:</p>
    <div class="as-custom-inputs">
      <input id="custom-name" class="as-custom-input" placeholder="Thema (z.B. Pensionsreform)" type="text">
      <input id="custom-kw" class="as-custom-input" placeholder="Kürzel (z.B. Pension)" type="text">
    </div>
    <button class="as-add-btn" onclick="asAddCustom()">+ Hinzufügen</button>
  </div>

  <div class="as-confirm-row">
    <span id="as-count" style="font-size:13px;color:var(--muted);font-family:var(--sans)">0 ausgewählt</span>
    <button class="as-btn-primary" onclick="asConfirm()">Speichern</button>
  </div>
</div>

<div id="as-sync" style="display:none">
  <p style="font-size:14px;font-family:var(--sans);margin:0 0 8px;font-weight:600">Telegram-Bot synchronisieren</p>
  <p style="font-size:13px;color:var(--muted);font-family:var(--sans);margin:0 0 6px">Sende diese Befehle an deinen Bot, damit auch die täglichen Lagebilder angepasst werden:</p>
  <div class="as-cmd-box" id="as-cmd-text"></div>
  <button class="tg-copy-btn" onclick="asCopyCmd()">Kopieren</button>
  <div style="margin-top:20px">
    <button class="as-btn-primary" onclick="asDone()">Fertig →</button>
  </div>
</div>

<div id="topic-list" style="display:none">
{topic_cards}
  <button class="reset-link" onclick="asReset()">Themen-Auswahl bearbeiten</button>
</div>

<script>
(function(){{
var TOPICS={topics_js};
var PREF_KEY='auf_stand_prefs';
var CUSTOM_KEY='auf_stand_custom';
var selected=new Set();
var customTopics=[];

function show(id){{['as-intro','as-cards','as-sync','topic-list'].forEach(function(i){{
  document.getElementById(i).style.display=i===id?'':'none';
}});}}

function filterTopics(prefs){{
  document.getElementById('topic-list').querySelectorAll('.dossier-topic').forEach(function(el){{
    el.style.display=(!prefs||prefs.indexOf(el.dataset.topicName)>=0)?'':'none';
  }});
}}

function updateCount(){{
  document.getElementById('as-count').textContent=selected.size+customTopics.length+' ausgewählt';
}}

// Init: Lade gespeicherte Präferenzen
try{{
  var saved=JSON.parse(localStorage.getItem(PREF_KEY)||'null');
  customTopics=JSON.parse(localStorage.getItem(CUSTOM_KEY)||'[]');
  if(saved&&saved.length){{show('topic-list');filterTopics(saved);}}
  else{{show('as-intro');}}
}}catch(e){{show('as-intro');}}

window.asOpen=function(){{
  // Lade bisherige Auswahl in Set
  try{{
    var saved=JSON.parse(localStorage.getItem(PREF_KEY)||'[]');
    selected=new Set(saved||[]);
  }}catch(e){{selected=new Set();}}
  // Karten-Zustand setzen
  document.querySelectorAll('.as-toggle-card').forEach(function(el){{
    if(selected.has(el.dataset.name))el.classList.add('selected');
    else el.classList.remove('selected');
  }});
  customTopics=JSON.parse(localStorage.getItem(CUSTOM_KEY)||'[]');
  updateCount();
  show('as-cards');
}};

window.asToggle=function(el){{
  var name=el.dataset.name;
  if(selected.has(name)){{selected.delete(name);el.classList.remove('selected');}}
  else{{selected.add(name);el.classList.add('selected');}}
  updateCount();
}};

window.asAddCustom=function(){{
  var name=document.getElementById('custom-name').value.trim();
  var kw=document.getElementById('custom-kw').value.trim();
  if(!name||!kw)return;
  customTopics.push({{name:name,kw:kw}});
  localStorage.setItem(CUSTOM_KEY,JSON.stringify(customTopics));
  selected.add(name);
  // Neue Toggle-Karte einfügen
  var cards=document.getElementById('as-cards');
  var section=cards.querySelector('.as-custom-section');
  var div=document.createElement('div');
  div.className='as-toggle-card selected';
  div.dataset.name=name;
  div.onclick=function(){{window.asToggle(div);}};
  div.innerHTML='<div class="as-card-check">✓</div><div><div class="as-card-name">'+name+'</div><div class="as-card-q">#'+kw+'</div></div>';
  cards.insertBefore(div,section);
  document.getElementById('custom-name').value='';
  document.getElementById('custom-kw').value='';
  updateCount();
}};

window.asConfirm=function(){{
  var prefs=Array.from(selected);
  localStorage.setItem(PREF_KEY,JSON.stringify(prefs));
  // Telegram-Befehle zusammenstellen
  var kws=prefs.map(function(n){{
    var t=TOPICS.find(function(t){{return t.name===n;}});
    return t?t.kw:null;
  }}).filter(Boolean);
  var lines=['/themen '+kws.join(' ')];
  customTopics.forEach(function(c){{lines.push('/thema-neu '+c.name+'|'+c.kw);}});
  document.getElementById('as-cmd-text').textContent=lines.join('\\n');
  show('as-sync');
}};

window.asCopyCmd=function(){{
  var t=document.getElementById('as-cmd-text').textContent;
  navigator.clipboard&&navigator.clipboard.writeText(t).then(function(){{
    var b=document.querySelector('.tg-copy-btn');
    b.textContent='✓ Kopiert';setTimeout(function(){{b.textContent='Kopieren';}},2000);
  }});
}};

window.asDone=function(){{
  var prefs=JSON.parse(localStorage.getItem(PREF_KEY)||'[]');
  show('topic-list');
  filterTopics(prefs.length?prefs:null);
}};

window.asReset=function(){{
  window.asOpen();
}};
}})();
</script>
"""

    content = "<h1>Meine Themen</h1>\n" + assessment_html
    html = _render_page("Meine Themen", content, "dossier")
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


_MANIFEST = {
    "name": "Auf Stand · Die Presse",
    "short_name": "Auf Stand",
    "description": "Dein tägliches Lagebild der Presse — in rund 90 Sekunden auf Stand.",
    "lang": "de-AT",
    "dir": "ltr",
    "start_url": "./index.html",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#ffffff",
    "theme_color": "#ffffff",
    "categories": ["news"],
    "icons": [
        {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}

# Service Worker: Seiten network-first (frisches Lagebild zuerst, Cache als
# Offline-Fallback), statische/Fremd-Assets cache-first. Cache-Version im Namen,
# damit ein Deploy alte Caches verdrängt.
_SERVICE_WORKER = """\
const CACHE = 'auf-stand-v1';
const SHELL = ['./', './index.html', './dossier.html', './archiv/index.html',
  './icon-192.png', './icon-512.png', './apple-touch-icon.png'];

self.addEventListener('install', function(e){
  self.skipWaiting();
  e.waitUntil(caches.open(CACHE).then(function(c){
    return Promise.all(SHELL.map(function(u){ return c.add(u).catch(function(){}); }));
  }));
});

self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(k){ return k !== CACHE; })
      .map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});

self.addEventListener('fetch', function(e){
  var req = e.request;
  if(req.method !== 'GET') return;
  var url = new URL(req.url);
  if(url.origin !== self.location.origin){
    // Fremd-Assets (Google Fonts): cache-first, lange haltbar.
    e.respondWith(caches.open(CACHE).then(function(c){
      return c.match(req).then(function(hit){
        return hit || fetch(req).then(function(res){
          try { c.put(req, res.clone()); } catch(err){}
          return res;
        }).catch(function(){ return hit; });
      });
    }));
    return;
  }
  // Eigene Seiten: network-first, Cache als Offline-Fallback.
  e.respondWith(fetch(req).then(function(res){
    if(res && res.ok){
      var copy = res.clone();
      caches.open(CACHE).then(function(c){ c.put(req, copy); });
    }
    return res;
  }).catch(function(){
    return caches.match(req).then(function(hit){
      return hit || caches.match('./index.html');
    });
  }));
});
"""


def _write_pwa_assets() -> None:
    """Schreibt Web-App-Manifest und Service Worker (Icons liegen als statische Dateien)."""
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "manifest.webmanifest").write_text(
        json.dumps(_MANIFEST, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (SITE_DIR / "sw.js").write_text(_SERVICE_WORKER, encoding="utf-8")


def build_site() -> Path:
    """Kopiert neue Ausgaben ins Archiv und baut alle Site-Seiten neu."""
    state: dict = {}
    try:
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    _write_pwa_assets()
    config_path = BASE_DIR / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    all_topics = config.get("topics", []) + state.get("custom_topics", [])
    build_dossier(
        state.get("dossier", {}),
        all_topics,
        state.get("topic_articles", {}),
        assessment_questions=state.get("assessment_questions"),
    )

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

    # Alle Archiv-Einzelseiten neu durchrendern, damit sie das aktuelle (helle)
    # Template tragen. Idempotent: _enhance_content fügt Highlights/Ressort/Byline
    # nur einmal ein, _add_article_feedback ersetzt bestehende Leisten.
    for (d, _rank, edition), path in editions:
        raw = path.read_text(encoding="utf-8")
        content = _extract_body(raw, d.isoformat(), edition)
        branded = _render_page(_label(d, edition), content, "archiv", root="../")
        path.write_text(branded, encoding="utf-8")

    build_archiv_index(editions)

    # Hauptseite: neueste Ausgabe — mit Streak-Ritus ganz oben.
    latest_html = editions[0][1].read_text(encoding="utf-8")
    latest_d, _, latest_edition = editions[0][0]
    latest_content = _extract_body(latest_html, latest_d.isoformat(), latest_edition)
    from . import state as state_mod
    streak = state_mod.current_streak(state)
    if streak >= 2:
        latest_content = (
            f'<div class="streak">🔥 {streak} Tage in Folge auf Stand</div>\n'
            + latest_content
        )
    title = _label(latest_d, latest_edition)
    index_html = _render_page(title, latest_content, "lagebild")
    index.write_text(index_html, encoding="utf-8")

    print(f"Web-App gebaut: {index} ({len(editions)} Ausgabe(n) im Archiv)")
    return index
