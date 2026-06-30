"""Baut die statische Web-App (site/) aus den erzeugten Lagebildern."""
from __future__ import annotations

import html as _html
import json
import re
import shutil
from datetime import date
from pathlib import Path

import yaml

from . import i18n as _i18n
from . import render as _render

BASE_DIR = Path(__file__).resolve().parent.parent
SITE_DIR = BASE_DIR / "site"
ARCHIV_DIR = SITE_DIR / "archiv"
STATE_PATH = BASE_DIR / "data" / "state.json"

_EDITION_RANK = {"catchup": 0, "morgen": 1, "mittag": 2, "nachmittag": 3, "abend": 4}
_EDITION_LABEL = {
    "morgen": "Morgen-Ausgabe", "mittag": "Mittags-Ausgabe",
    "nachmittag": "Nachmittags-Ausgabe", "abend": "Abend-Ausgabe",
    "catchup": "Catch-up",
}
_EDITION_LABEL_EN = {
    "morgen": "Morning Briefing", "mittag": "Midday Update",
    "nachmittag": "Afternoon Update", "abend": "Evening Briefing",
    "catchup": "Catch-up",
}
# Presse-Kuratierungszeiten je Ausgabe (für die dezente Rhythmus-Anzeige).
_EDITION_TIME = {"morgen": "06:00", "mittag": "11:00", "nachmittag": "16:00", "abend": "20:00"}
_EDITION_ORDER = ["morgen", "mittag", "nachmittag", "abend"]
_EDITIONS_RE = "morgen|mittag|nachmittag|abend|catchup"
_FILENAME_RE = re.compile(rf"^(\d{{4}})-(\d{{2}})-(\d{{2}})-({_EDITIONS_RE})\.html$")

# ---------------------------------------------------------------------------
# Design-System — Die Presse · Copilot (Light, „Presse-Stil"; Richtung C:
# Briefing-Timeline). Klares Weiß, editoriale Serif-Schlagzeilen (Newsreader),
# tiefes Redaktions-Blau als sparsamer Akzent, schwebende Pill-Tableiste.
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
_ICON_NYT = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
             '<circle cx="12" cy="12" r="9"/>'
             '<path d="M3.6 9h16.8M3.6 15h16.8"/>'
             '<path d="M12 3c-2 3-2 15 0 18"/><path d="M12 3c2 3 2 15 0 18"/>'
             '</svg>')
_ICON_PRESSE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
                '<rect x="4" y="4" width="16" height="16" rx="2"/>'
                '<path d="M8 9h8M8 12h5M8 15h3"/>'
                '</svg>')

_PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="robots" content="noindex">
  <meta name="theme-color" content="#ffffff">
  <link rel="manifest" href="__ROOT__manifest.webmanifest">
  <script src="__ROOT__push-config.js"></script>
  <link rel="icon" href="__ROOT__favicon-32.png" sizes="32x32" type="image/png">
  <link rel="apple-touch-icon" href="__ROOT__apple-touch-icon.png">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="Copilot">
  <meta name="application-name" content="Copilot">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;0,6..72,700;1,6..72,400&family=Archivo:wght@400;500;600;700&display=swap" rel="stylesheet">
  <title>__TITLE__ · Die Presse · Copilot</title>
  <style>
    /* Copilot · Die Presse — Richtung C „Briefing-Timeline" (Light, Presse-Stil)
       Schriften: Newsreader (editoriale Serif für Schlagzeilen), Archivo (UI + Text).
       Akzent: tiefes Redaktions-Blau #2d4f9e als sparsamer Akzent; klares Weiß,
       Haarlinien statt verspielter Karten; Streak in Bernstein. */
    :root {
      --bg: #ffffff; --surface: #ffffff; --surface-tint: #f6f7f9;
      --border: rgba(0,0,0,.10); --border-soft: rgba(0,0,0,.07);
      --card-border: rgba(0,0,0,.06);
      --text: #16233a; --text-alt: #1c2b3d; --text-body: #22304a;
      --fg: #566173; --muted: #6a7382; --dim: #97a0ab;
      --accent: #2d4f9e; --accent-soft: rgba(45,79,158,.10);
      --accent-shadow: rgba(45,79,158,.45);
      --streak: #c8791b; --streak-text: #a8650f;
      --serif: 'Newsreader', Georgia, 'Times New Roman', serif;
      --sans: 'Archivo', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { height: -webkit-fill-available; }
    body {
      background: #e7e5df; color: var(--text); font-family: var(--sans);
      -webkit-font-smoothing: antialiased;
      display: flex; flex-direction: column;
      height: 100vh; height: -webkit-fill-available; overflow: hidden;
    }
    /* ── App-Shell (zentrierte Handy-Säule) ── */
    .app {
      position: relative;
      max-width: 430px; width: 100%; margin: 0 auto; background: var(--bg);
      display: flex; flex-direction: column;
      height: 100vh; height: -webkit-fill-available; overflow: hidden;
    }
    /* ── Scroll-Bereich ── */
    .scroll-area { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    /* ── Topbar (Masthead im Presse-Stil) ── */
    .topbar {
      background: var(--surface); border-bottom: 1px solid var(--border);
      flex-shrink: 0;
    }
    .brandrow {
      display: flex; align-items: center; justify-content: space-between;
      padding: 12px 22px 12px;
    }
    .wordmark-text {
      font-family: var(--serif); font-weight: 600; font-size: 23px;
      letter-spacing: .2px; color: var(--text-alt);
    }
    .copilot-pill {
      display: inline-flex; align-items: center; padding: 5px 12px;
      border-radius: 20px; font: 700 10px var(--sans);
      letter-spacing: .14em; text-transform: uppercase;
      background: var(--accent-soft); color: var(--accent);
    }
    .progress-track { height: 2px; background: var(--surface-tint); }
    .progress-bar {
      height: 100%; border-radius: 0 2px 2px 0;
      background: var(--accent); width: 0; transition: width .12s linear;
    }
    /* ── Masthead ausblenden (Topbar übernimmt) ── */
    .masthead { display: none; }
    /* ── Layout (Platz unten für die schwebende Tableiste) ── */
    .wrap { padding: 4px 0 116px; }
    /* ── Typografie ── */
    h1 {
      font-family: var(--serif); font-size: 2.5rem; line-height: 1.0;
      margin: 0 0 12px; font-weight: 500; color: var(--text); letter-spacing: -.5px;
    }
    h2 {
      font-family: var(--serif); font-size: 1.5rem; line-height: 1.14;
      margin: 0 0 10px; font-weight: 500; color: var(--text); letter-spacing: -.3px;
    }
    p { margin: 0 0 13px; color: var(--fg); font-size: 15px; line-height: 1.6; }
    strong {
      font-family: var(--sans); font-size: 11px; letter-spacing: .14em;
      text-transform: uppercase; color: var(--accent); font-weight: 700;
    }
    em { font-style: italic; color: var(--muted); }
    hr { border: none; border-top: 1px solid var(--border); margin: 0; }
    /* ── Lagebild-Kopf (randlos, editorial) ── */
    .lagebild-header {
      background: transparent; border-radius: 0; box-shadow: none;
      padding: 24px 22px 0; margin: 0;
    }
    .kicker {
      font: 700 11.5px var(--sans); letter-spacing: .16em; text-transform: uppercase;
      color: var(--accent); margin: 0 0 14px;
    }
    .lagebild-header h1 { margin: 0; }
    .next-edition { font: 400 13px var(--sans); color: var(--muted); margin: 12px 0 0; }
    /* ── Byline (Rule darüber, wie im Presse-Feed) ── */
    .byline {
      font: 400 14px var(--sans); color: var(--muted);
      padding-top: 16px; border-top: 1px solid var(--border); margin: 20px 0 0;
    }
    /* ── Streak (Bernstein-Akzent) ── */
    .streak {
      display: inline-flex; align-items: center; gap: 6px;
      font: 700 12px var(--sans); color: var(--streak-text);
      background: rgba(200,121,27,.12); border: 1px solid rgba(200,121,27,.25);
      border-radius: 20px; padding: 5px 12px; margin: 12px 0 0;
    }
    /* ── Briefing-Timeline (Richtung C: der Kuratierungs-Takt als Held) ── */
    .timeline {
      background: var(--surface-tint); border-radius: 18px;
      padding: 18px 20px 16px; margin: 22px 0 6px;
    }
    .tl-label {
      font: 700 11px var(--sans); letter-spacing: .16em; text-transform: uppercase;
      color: var(--dim); margin: 0 0 18px;
    }
    .tl-track {
      position: relative; display: flex; justify-content: space-between;
      align-items: center; margin: 0 8px;
    }
    .tl-track::before {
      content: ""; position: absolute; left: 0; right: 0; top: 50%;
      height: 2px; background: var(--border); transform: translateY(-50%);
    }
    .tl-fill {
      position: absolute; left: 0; top: 50%; height: 2px;
      background: var(--accent); transform: translateY(-50%);
      transition: width .4s ease;
    }
    .tl-node {
      position: relative; z-index: 1; width: 26px; height: 26px;
      border-radius: 50%; background: #fff; border: 2px solid var(--border);
      color: var(--dim); font: 700 10.5px var(--sans);
      display: flex; align-items: center; justify-content: center;
    }
    .tl-node.done { background: var(--accent); border-color: var(--accent); color: #fff; }
    .tl-node.now {
      background: var(--accent); border-color: var(--accent); color: #fff;
      box-shadow: 0 0 0 6px var(--accent-soft); transform: scale(1.14);
    }
    .tl-caption { font: 400 13px var(--sans); color: var(--muted); margin: 18px 0 0; text-align: center; }
    .tl-caption b { color: var(--accent); font-weight: 700; }
    /* ── Audio-Player (Inset) ── */
    .audio-player {
      background: var(--surface-tint); border: 1px solid var(--card-border);
      border-radius: 14px; padding: 14px 16px; margin: 6px 22px; box-shadow: none;
    }
    .audio-player .audio-label {
      display: block; font: 700 11px var(--sans); letter-spacing: .12em;
      text-transform: uppercase; color: var(--muted); margin-bottom: 8px;
    }
    .audio-player audio { width: 100%; height: 40px; }
    /* ── „Heute wichtig" als nummerierte editoriale Liste (Richtung C) ── */
    .highlights {
      background: transparent; border-radius: 0; box-shadow: none;
      padding: 28px 22px 0; margin: 0; counter-reset: hl;
    }
    /* Label-Zeile („Heute wichtig:") als dezentes Sektions-Label + Rule darunter */
    .highlights p:has(strong) {
      margin: 0; padding: 0 0 4px; border-bottom: 1px solid var(--border);
    }
    .highlights p:has(strong) strong {
      display: block; color: var(--dim); font-size: 11.5px; letter-spacing: .16em;
    }
    /* Eintragszeilen: blaue 01/02/03 + Serif-Schlagzeile, Haarlinien dazwischen */
    .highlights p:not(:has(strong)) {
      counter-increment: hl; position: relative;
      margin: 0; padding: 16px 0 16px 34px;
      border-bottom: 1px solid var(--border-soft);
      font-family: var(--serif); font-size: 18px; line-height: 1.3; color: var(--text-body);
    }
    .highlights p:not(:has(strong))::before {
      content: counter(hl, decimal-leading-zero);
      position: absolute; left: 0; top: 18px;
      font: 700 12px var(--sans); color: var(--accent); letter-spacing: .5px;
    }
    .highlights p:not(:has(strong)):last-child { border-bottom: none; }
    /* ── Story-Sektionen (randlos, durch Haarlinien getrennt — Presse-Feed) ── */
    .story-card {
      background: transparent; border-radius: 0; box-shadow: none;
      padding: 24px 22px 8px; margin: 0; border-top: 1px solid var(--border);
    }
    /* Fallback: h2 außerhalb story-card (dossier/archiv) */
    h2 { margin: 28px 0 10px; }
    /* ── Accordion (Story-Sektionen) ── */
    .story-head {
      display: flex; gap: 12px; align-items: flex-start;
      cursor: pointer; padding: 0 0 12px;
    }
    .story-head h2 { flex: 1; margin: 0; padding: 0; }
    .story-head .chev {
      flex: none; width: 27px; height: 27px; border-radius: 50%;
      background: var(--surface-tint); color: var(--dim);
      font-family: var(--serif); font-size: 17px;
      display: flex; align-items: center; justify-content: center;
      line-height: 1; flex-shrink: 0; margin-top: 2px;
    }
    .story-body { max-height: 0; opacity: 0; overflow: hidden;
      transition: max-height .3s ease, opacity .2s ease; }
    .story-card.open .story-body { max-height: 2000px; opacity: 1;
      transition: max-height .45s ease, opacity .35s ease; }
    .story-body p { color: var(--fg); }
    /* ── „Was ist neu / Warum es zählt" als WARUM-Mikrozeile (Richtung C) ── */
    .story-body p > strong:first-child {
      display: block; margin-bottom: 4px; font-size: 11px; letter-spacing: .14em;
    }
    /* ── Ressort-Tag ── */
    .ressort {
      display: inline-block; background: var(--accent-soft); color: var(--accent);
      border-radius: 999px; padding: 3px 10px; font: 600 10.5px var(--sans);
      letter-spacing: .06em; text-transform: uppercase; vertical-align: middle; margin-right: 6px;
    }
    /* ── Quell-Link als Pill ── */
    .source-link {
      display: inline-block; background: var(--accent); color: #fff;
      border-radius: 999px; padding: 6px 16px; font: 600 12px var(--sans);
      letter-spacing: .03em; text-decoration: none; margin-top: 4px;
      transition: filter .15s;
    }
    .source-link:hover { filter: brightness(.9); text-decoration: none; }
    .byline-source { font: italic 12px var(--sans); color: var(--muted); white-space: nowrap; }
    .reporters {
      font: 400 13px var(--sans); color: var(--muted);
      margin: 6px 22px 0; padding-top: 14px; border-top: 1px solid var(--border);
    }
    /* ── Done-Box („Du bist informiert ✓") ── */
    .done {
      background: var(--surface-tint); border: 1px solid var(--card-border);
      border-radius: 14px; padding: 16px 18px; margin: 18px 22px 6px; box-shadow: none;
      font: 600 13px var(--sans); color: #1f7a52;
      display: flex; align-items: center; gap: 8px;
    }
    .done-check {
      width: 20px; height: 20px; border-radius: 50%; background: #1f7a52;
      color: #fff; display: inline-flex; align-items: center; justify-content: center;
      font-size: 12px; flex-shrink: 0;
    }
    /* ── Deine-Themen Karte (kein Accordion) ── */
    .topic-summary-head {
      font: 700 11px var(--sans); letter-spacing: .12em; text-transform: uppercase;
      color: var(--muted); margin: 0 0 12px;
    }
    .story-card:has(.topic-summary-head) .story-head { cursor: default; }
    /* ── Archiv ── */
    .archiv-grid {
      display: flex; flex-direction: column; gap: 8px;
      margin: 8px 16px 0;
    }
    .archiv-card {
      display: block; background: var(--surface); border-radius: 16px;
      padding: 15px 18px; box-shadow: 0 1px 3px rgba(22,32,43,.05);
      border: 1px solid var(--card-border); transition: border-color .15s;
    }
    .archiv-card:hover { border-color: var(--accent); text-decoration: none; }
    .archiv-date { display: block; font: 600 14px var(--sans); color: var(--text); margin-bottom: 3px; }
    .archiv-label { display: block; font: 400 12px var(--sans); color: var(--muted); }
    /* ── Dossier / Themen ── */
    .dossier-topic {
      background: var(--surface); border: 1px solid var(--card-border);
      border-radius: 16px; padding: 18px 20px;
      margin: 8px 16px; box-shadow: 0 1px 3px rgba(22,32,43,.05);
    }
    .dossier-topic h2 {
      margin: 0 0 12px; border-bottom: 1px solid var(--border); padding-bottom: 10px;
    }
    .dossier-entries { list-style: none; padding: 0; margin: 0; }
    .dossier-entries li {
      padding: 9px 0; border-bottom: 1px solid var(--border);
      display: flex; gap: 12px; align-items: baseline; font-size: 14px; color: var(--fg);
    }
    .dossier-entries li:last-child { border-bottom: none; }
    .dossier-date { font: 600 12px var(--sans); color: var(--accent); white-space: nowrap; min-width: 68px; }
    .empty-state {
      color: var(--muted); font-style: italic; padding: 32px 16px;
      text-align: center; font: 400 15px var(--sans);
    }
    /* ── Tab-Leiste (schwebende Pille — wie in der Presse-App) ── */
    .tabbar {
      position: absolute; left: 14px; right: 14px;
      bottom: calc(18px + env(safe-area-inset-bottom));
      height: 66px; border-radius: 30px; z-index: 30;
      background: rgba(255,255,255,.82);
      -webkit-backdrop-filter: blur(18px); backdrop-filter: blur(18px);
      border: 1px solid var(--card-border);
      box-shadow: 0 8px 24px -8px rgba(0,0,0,.18);
      display: flex; padding: 0 6px;
    }
    .tab {
      flex: 1; display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 3px; color: #8a929e;
      font: 600 10px var(--sans); letter-spacing: .04em; text-transform: uppercase;
      transition: color .15s;
    }
    .tab:hover { color: var(--text); text-decoration: none; }
    .tab svg { width: 22px; height: 22px; }
    .tab.active { color: var(--accent); font-weight: 700; }
    /* ── Artikel-Feedback ── */
    .article-fb { display: flex; gap: 8px; margin: 12px 0 4px; flex-wrap: wrap; }
    .fb-btn {
      display: inline-flex; align-items: center; gap: 5px;
      background: var(--surface-tint); border: 1px solid var(--card-border); border-radius: 999px;
      padding: 8px 16px; font: 600 12px var(--sans); cursor: pointer;
      color: var(--muted); transition: all .15s; line-height: 1;
    }
    .fb-btn:hover { filter: brightness(.97); }
    .fb-btn.active[data-vote="up"] {
      background: var(--accent); color: #fff;
      box-shadow: 0 4px 12px -4px var(--accent-shadow);
    }
    .fb-btn.active[data-vote="down"] { background: #28303a; color: #fff; }
    /* ── Themen-Reiter ── */
    .schlagwort-badge {
      display: inline-block; font: 600 11px var(--sans); color: var(--accent);
      background: var(--accent-soft); border-radius: 999px;
      padding: 2px 8px; margin-left: 8px; vertical-align: middle; letter-spacing: .03em;
    }
    .dossier-empty { color: var(--muted); font-style: italic; font: 400 13px var(--sans); padding: 6px 0; }
    .topic-stand { font: italic 13px var(--sans); color: var(--muted); margin: 4px 0 10px; }
    .topic-articles { list-style: none; padding: 0; margin: 0; }
    .topic-article { padding: 9px 0; border-bottom: 1px solid var(--border); }
    .topic-article:last-child { border-bottom: none; }
    .topic-article a {
      color: var(--fg); text-decoration: none; display: flex;
      justify-content: space-between; align-items: baseline; gap: 10px;
    }
    .topic-article-title { flex: 1; font-size: 14px; line-height: 1.4; }
    .topic-article-date { font: 400 12px var(--sans); color: var(--muted); white-space: nowrap; }
    /* ── Assessment v2 (Toggle-Karten) ── */
    .as-intro-text { font: 400 15px var(--sans); color: var(--muted); line-height: 1.6; margin-bottom: 18px; }
    .as-btn-primary {
      background: var(--accent); color: #fff; font-weight: 600; border-radius: 999px;
      padding: 13px 28px; font-size: 15px; cursor: pointer; font-family: var(--sans);
      border: none; display: inline-block; transition: filter .15s;
    }
    .as-btn-primary:hover { filter: brightness(.93); }
    .as-toggle-card {
      display: flex; gap: 14px; align-items: flex-start; padding: 14px;
      border: 1.5px solid var(--border); border-radius: 14px; margin: 8px 0;
      cursor: pointer; transition: border-color .15s, background .15s;
      user-select: none; background: var(--surface);
    }
    .as-toggle-card.selected {
      border-color: rgba(45,79,158,.35); background: var(--accent-soft);
    }
    .as-card-check {
      width: 24px; height: 24px; border-radius: 50%; border: 1.5px solid #d4dae2;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      font-size: 13px; color: transparent; margin-top: 1px; transition: all .15px;
    }
    .as-toggle-card.selected .as-card-check {
      background: var(--accent); border-color: var(--accent); color: #fff;
    }
    .as-card-name { font: 600 14.5px var(--sans); margin-bottom: 3px; line-height: 1.3; }
    .as-card-q { font: 400 12.5px var(--sans); color: var(--muted); line-height: 1.42; margin-top: 5px; }
    .as-custom-section { border-top: 1px solid var(--border); padding-top: 18px; margin-top: 12px; }
    .as-custom-inputs { display: flex; gap: 8px; margin: 10px 0 12px; flex-wrap: wrap; }
    .as-custom-input {
      flex: 1; min-width: 130px; background: var(--surface);
      border: 1px solid var(--border); border-radius: 10px;
      padding: 10px 12px; color: var(--fg); font: 400 14px var(--sans); outline: none;
    }
    .as-custom-input:focus { border-color: var(--accent); }
    .as-add-btn {
      background: none; border: 1px solid var(--border); border-radius: 999px;
      padding: 10px 18px; color: var(--fg); font: 400 14px var(--sans);
      cursor: pointer; white-space: nowrap; transition: border-color .15s;
    }
    .as-add-btn:hover { border-color: var(--accent); }
    .as-confirm-row {
      display: flex; justify-content: space-between; align-items: center;
      margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border);
    }
    .as-cmd-box {
      background: var(--surface-tint); border: 1px solid var(--border); border-radius: 10px;
      padding: 14px; margin: 10px 0 16px; font-family: monospace; font-size: 13px;
      color: var(--accent); white-space: pre-wrap; line-height: 1.7;
    }
    .tg-copy-btn {
      background: none; border: 1px solid var(--border); border-radius: 6px;
      padding: 5px 12px; font: 400 12px var(--sans); color: var(--muted);
      cursor: pointer; margin-left: 8px;
    }
    .reset-link {
      font: 400 12px var(--sans); color: var(--muted); text-decoration: underline;
      cursor: pointer; margin-top: 20px; display: inline-block; background: none;
      border: none; padding: 0;
    }
    /* ── Cross-link chip ── */
    .crosslink {
      font: 400 12px var(--sans); color: var(--muted);
      padding: 12px 22px 0; display: block;
    }
  </style>
</head>
<body>
<div class="app">
<div class="topbar">
  <div class="brandrow">
    <div class="wordmark-text">Die Presse</div>
    <div class="copilot-pill">Copilot</div>
  </div>
  <div class="progress-track"><div class="progress-bar" id="__pb"></div></div>
</div>
<div class="scroll-area" id="__sa">
<div class="wrap">
__CONTENT__
</div>
</div>
<nav class="tabbar">
  <a href="__ROOT__index.html" class="tab __NAV_LAGEBILD__">__ICON_HOME__<span>Lagebild</span></a>
  <a href="__ROOT__dossier.html" class="tab __NAV_DOSSIER__">__ICON_DOSSIER__<span>Themen</span></a>
  <a href="__ROOT__archiv/index.html" class="tab __NAV_ARCHIV__">__ICON_ARCHIV__<span>Archiv</span></a>
  <a href="https://www.diepresse.com/epaper" class="tab" target="_blank" rel="noopener">__ICON_EPAPER__<span>E-Paper</span></a>
  <a href="__ROOT__nyt/" class="tab">__ICON_NYT__<span>NYT</span></a>
</nav>
</div>
<script>
(function(){
  // Lesefortschritts-Balken
  var sa=document.getElementById('__sa'), pb=document.getElementById('__pb');
  if(sa&&pb){
    sa.addEventListener('scroll',function(){
      var max=sa.scrollHeight-sa.clientHeight;
      pb.style.width=(max>0?Math.round(sa.scrollTop/max*100):0)+'%';
    },{passive:true});
  }
  // Briefing-Timeline live an die echte Wiener Uhrzeit koppeln: aktiver Knoten
  // + mitlaufender Countdown zur nächsten Ausgabe (06/11/16/20). Die im Build
  // erzeugte Version ist der No-JS-Fallback; hier wird sie zur Laufzeit aktuell.
  (function(){
    var tl=document.querySelector('.timeline');
    if(!tl) return;
    var fill=tl.querySelector('.tl-fill');
    var nodes=tl.querySelectorAll('.tl-node');
    var cap=tl.querySelector('.tl-caption');
    var SLOTS=[6,11,16,20];
    function viennaNow(){
      try{
        var p=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Vienna',hour12:false,
          hour:'2-digit',minute:'2-digit',second:'2-digit'}).formatToParts(new Date());
        var h=0,m=0,s=0;
        p.forEach(function(x){ if(x.type==='hour')h=+x.value;
          else if(x.type==='minute')m=+x.value; else if(x.type==='second')s=+x.value; });
        return (h%24)*60+m+s/60;
      }catch(e){ var d=new Date(); return d.getHours()*60+d.getMinutes()+d.getSeconds()/60; }
    }
    function fmtDur(mins){
      mins=Math.max(0,Math.ceil(mins));
      if(mins<1) return 'gleich';
      var h=Math.floor(mins/60), m=mins%60;
      if(h>0) return 'in '+h+' Std'+(m>0?' '+m+' Min':'');
      return 'in '+m+' Min';
    }
    function pad(n){ return (n<10?'0':'')+n; }
    function update(){
      var now=viennaNow(), cur=-1, i;
      for(i=0;i<SLOTS.length;i++){ if(now>=SLOTS[i]*60) cur=i; }
      var nextIdx, when, until, prog;
      if(cur===-1){ nextIdx=0; when='heute'; until=SLOTS[0]*60-now; prog=0; }
      else if(cur===SLOTS.length-1){ nextIdx=0; when='morgen'; until=(24*60-now)+SLOTS[0]*60; prog=1; }
      else { nextIdx=cur+1; when='heute'; until=SLOTS[nextIdx]*60-now;
        prog=(cur+(now-SLOTS[cur]*60)/(SLOTS[nextIdx]*60-SLOTS[cur]*60))/(SLOTS.length-1); }
      for(i=0;i<nodes.length;i++){
        nodes[i].className='tl-node'+(i<cur?' done':(i===cur?' now':''));
      }
      if(fill) fill.style.width=Math.round(Math.max(0,Math.min(1,prog))*100)+'%';
      if(cap) cap.innerHTML='Nächste Aktualisierung <b>'+fmtDur(until)+'</b> · '
        +when+' '+pad(SLOTS[nextIdx])+':00 Uhr';
    }
    update();
    setInterval(update,30000);
  })();
  // Story-Sektionen in Karten verpacken (h2…hr → .story-card)
  (function(){
    var wrap=document.querySelector('.wrap');
    if(!wrap) return;
    var nodes=Array.from(wrap.childNodes);
    var card=null;
    nodes.forEach(function(n){
      var tag=n.nodeType===1?n.tagName:'';
      if(tag==='H2'){
        card=document.createElement('div');
        card.className='story-card';
        n.parentNode.insertBefore(card,n);
        card.appendChild(n);
      } else if(tag==='HR'){
        card=null;
        wrap.removeChild(n);
      } else if(card){
        card.appendChild(n);
      }
    });
  })();
  // Accordion: Story-Karten auf-/zuklappbar machen
  (function(){
    document.querySelectorAll('.story-card').forEach(function(card){
      var h2=card.querySelector('h2');
      if(!h2) return;
      // "Deine Themen" und andere Sonder-h2 nicht als Accordion behandeln
      if(h2.classList.contains('topic-summary-head')) return;
      // Ressort-Tag aus dem Body holen und vor h2 platzieren
      var ressort=card.querySelector('.ressort');
      if(ressort){
        var tagWrap=document.createElement('div');
        tagWrap.appendChild(ressort);
        h2.parentNode.insertBefore(tagWrap,h2);
      }
      // Body-Wrapper für alles nach h2
      var body=document.createElement('div');
      body.className='story-body';
      var sib=h2.nextSibling;
      while(sib){ var nx=sib.nextSibling; body.appendChild(sib); sib=nx; }
      // Chevron-Button
      var chev=document.createElement('span');
      chev.className='chev'; chev.textContent='–';
      // Head-Wrapper
      var head=document.createElement('div');
      head.className='story-head';
      card.insertBefore(head,h2);
      head.appendChild(h2);
      head.appendChild(chev);
      card.appendChild(body);
      card.classList.add('open');
      head.addEventListener('click',function(){
        card.classList.toggle('open');
        chev.textContent=card.classList.contains('open')?'–':'+';
      });
    });
  })();
  // Artikel-Feedback
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
  // PWA: Service Worker registrieren
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

# NYT-Edition-Template: abgeleitet vom Presse-Template, nur Brand/Labels/JS-Strings
# auf Englisch umgestellt. Strukturell und CSS identisch — Änderungen an _PAGE_TEMPLATE
# wirken automatisch durch. __NYT_EPAPER_URL__ wird in _render_nyt_page() ersetzt.
_NYT_PAGE_TEMPLATE = (
    _PAGE_TEMPLATE
    .replace(
        "<html lang=\"de\">",
        "<html lang=\"en\">"
    )
    .replace(
        "<title>__TITLE__ · Die Presse · Copilot</title>",
        "<title>__TITLE__ · NYT Briefing</title>"
    )
    .replace(
        "<div class=\"wordmark-text\">Die Presse</div>",
        "<div class=\"wordmark-text\">New York Times</div>"
    )
    .replace(
        "<span>Lagebild</span>",
        "<span>Briefing</span>"
    )
    .replace(
        "<span>Themen</span>",
        "<span>Topics</span>"
    )
    .replace(
        "<span>Archiv</span>",
        "<span>Archive</span>"
    )
    .replace(
        "<a href=\"https://www.diepresse.com/epaper\" class=\"tab\" target=\"_blank\" rel=\"noopener\">__ICON_EPAPER__<span>E-Paper</span></a>",
        "<a href=\"__NYT_EPAPER_URL__\" class=\"tab\" target=\"_blank\" rel=\"noopener\">__ICON_EPAPER__<span>Today's Paper</span></a>"
    )
    .replace(
        "<a href=\"__ROOT__nyt/\" class=\"tab\">__ICON_NYT__<span>NYT</span></a>",
        "<a href=\"__ROOT__../\" class=\"tab\">__ICON_PRESSE__<span>Presse</span></a>"
    )
    # JS timeline: German → English countdown strings
    .replace("if(mins<1) return 'gleich';", "if(mins<1) return 'now';")
    .replace(
        "if(h>0) return 'in '+h+' Std'+(m>0?' '+m+' Min':'');",
        "if(h>0) return 'in '+h+' hr'+(h>1?'s':'')+(m>0?' '+m+' min':'');"
    )
    .replace("return 'in '+m+' Min';", "return 'in '+m+' min';")
    .replace(
        "if(cur===-1){ nextIdx=0; when='heute'; until=SLOTS[0]*60-now; prog=0; }",
        "if(cur===-1){ nextIdx=0; when='today'; until=SLOTS[0]*60-now; prog=0; }"
    )
    .replace(
        "else if(cur===SLOTS.length-1){ nextIdx=0; when='morgen'; until=(24*60-now)+SLOTS[0]*60; prog=1; }",
        "else if(cur===SLOTS.length-1){ nextIdx=0; when='tomorrow'; until=(24*60-now)+SLOTS[0]*60; prog=1; }"
    )
    .replace(
        "else { nextIdx=cur+1; when='heute'; until=SLOTS[nextIdx]*60-now;",
        "else { nextIdx=cur+1; when='today'; until=SLOTS[nextIdx]*60-now;"
    )
    .replace(
        "if(cap) cap.innerHTML='Nächste Aktualisierung <b>'+fmtDur(until)+'</b> · '\n        +when+' '+pad(SLOTS[nextIdx])+':00 Uhr';",
        "if(cap) cap.innerHTML='Next update <b>'+fmtDur(until)+'</b> · '\n        +when+' at '+pad(SLOTS[nextIdx])+':00';"
    )
)


def _render_page(title: str, content: str, active: str, root: str = "") -> str:
    """Füllt das Presse-Page-Template mit Inhalt und aktivem Tab."""
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
        .replace("__ICON_NYT__", _ICON_NYT)
        .replace("__CONTENT__", content)
    )


def _render_nyt_page(
    title: str, content: str, active: str, root: str = "",
    epaper_url: str = "https://www.nytimes.com/section/todayspaper",
) -> str:
    """Füllt das NYT-Page-Template mit Inhalt und aktivem Tab."""
    nav = {"lagebild": "", "dossier": "", "archiv": ""}
    if active in nav:
        nav[active] = "active"
    return (
        _NYT_PAGE_TEMPLATE
        .replace("__TITLE__", title)
        .replace("__ROOT__", root)
        .replace("__NAV_LAGEBILD__", nav["lagebild"])
        .replace("__NAV_DOSSIER__", nav["dossier"])
        .replace("__NAV_ARCHIV__", nav["archiv"])
        .replace("__ICON_HOME__", _ICON_HOME)
        .replace("__ICON_DOSSIER__", _ICON_DOSSIER)
        .replace("__ICON_ARCHIV__", _ICON_ARCHIV)
        .replace("__ICON_EPAPER__", _ICON_EPAPER)
        .replace("__ICON_PRESSE__", _ICON_PRESSE)
        .replace("__NYT_EPAPER_URL__", epaper_url)
        .replace("__CONTENT__", content)
    )


# Ressort → oklch-Hue-Winkel (farbcodierte Tags wie im Die-Presse-Design-System).
_RESSORT_HUE = {
    "politik": 245, "wirtschaft": 175, "unternehmen": 175, "börse": 175,
    "international": 265, "ausland": 265, "europa": 265,
    "recht": 35, "justiz": 35, "energie": 75, "umwelt": 130,
    "wissenschaft": 150, "tech": 150, "technik": 150, "digital": 150,
    "wien": 25, "lokales": 25, "chronik": 25, "sport": 200, "kultur": 300,
    # NYT sections
    "homepage": 245, "world": 265, "us": 25, "politics": 245,
    "business": 175, "technology": 150, "science": 150, "climate": 130,
}

_BYLINE = 'Von der „Presse"-Redaktion'
_NYT_BYLINE = "By the New York Times briefing desk"


def _ressort_tag_str(name: str) -> str:
    name = name.strip()
    hue = _RESSORT_HUE.get(name.split("/")[0].split()[0].lower(), 24)
    return f'<span class="ressort" style="--h:{hue}">{name}</span>'


def _meta_tag(m: re.Match) -> str:
    """„(Ressort · Bericht: Name)" → Ressort-Pill + Quellenzeile (Deutsch)."""
    ressort, _, bericht = m.group(1).partition("·")
    out = _ressort_tag_str(ressort)
    if "Bericht:" in bericht:
        name = bericht.split("Bericht:", 1)[1].strip()
        if name:
            out += f' <span class="byline-source">Bericht: {name}</span>'
    return out + " "


def _meta_tag_en(m: re.Match) -> str:
    """„(Ressort · By: Name)" → Ressort-Pill + Quellenzeile (Englisch)."""
    ressort, _, by_part = m.group(1).partition("·")
    out = _ressort_tag_str(ressort)
    if "By:" in by_part:
        name = by_part.split("By:", 1)[1].strip()
        if name:
            out += f' <span class="byline-source">By: {name}</span>'
    return out + " "


_GREETING_POOL: dict[str, list[str]] = {
    "morgen": [
        "Guten Morgen.",
        "Schön, dass du da bist.",
        "Ein neuer Tag.",
        "Guten Morgen. Los geht's.",
        "Bereit?",
        "Guten Morgen. Hier ist er.",
        "Frisch informiert starten.",
    ],
    "mittag": [
        "Guten Tag.",
        "Kurze Pause.",
        "Halbzeit.",
        "Schön, dass du schaust.",
        "Mitten im Tag.",
        "Guten Tag. Kurz.",
        "Der Überblick zur Mittagszeit.",
    ],
    "nachmittag": [
        "Guten Nachmittag.",
        "Fast geschafft.",
        "Kurz innehalten.",
        "Schön, dass du da bist.",
        "Der Nachmittag, kompakt.",
        "Noch ein Blick.",
        "Guten Nachmittag. Da sind wir.",
    ],
    "abend": [
        "Guten Abend.",
        "Feierabend — fast.",
        "Der Tag, kompakt.",
        "Schön, dass du da bist.",
        "Was bleibt vom Tag.",
        "Guten Abend. Kurz noch.",
        "Der Abend gehört dir.",
    ],
    "catchup": [
        "Willkommen zurück.",
        "Schön, dass du wieder da bist.",
        "Was sich getan hat.",
        "Willkommen. Kurz nachgeholt.",
        "Die letzten Tage, kompakt.",
    ],
}

_GREETING_POOL_EN: dict[str, list[str]] = {
    "morgen": [
        "Good morning.",
        "Here's what happened.",
        "A new day.",
        "Good morning. Let's go.",
        "Ready?",
        "Good morning. Here it is.",
        "Start informed.",
    ],
    "mittag": [
        "Good afternoon.",
        "A quick pause.",
        "Midday check-in.",
        "Here's the latest.",
        "Halfway through the day.",
        "Good afternoon. Briefly.",
        "The midday picture.",
    ],
    "nachmittag": [
        "Good afternoon.",
        "Almost there.",
        "A moment to catch up.",
        "Here's what's new.",
        "The afternoon, compact.",
        "One more look.",
        "Good afternoon. Here we are.",
    ],
    "abend": [
        "Good evening.",
        "The day, in brief.",
        "What the day leaves behind.",
        "Good evening. Quick.",
        "The evening is yours.",
        "End of day briefing.",
        "What mattered today.",
    ],
    "catchup": [
        "Welcome back.",
        "Good to have you here.",
        "What you missed.",
        "Welcome. Caught up quickly.",
        "The last few days, compact.",
    ],
}


def _pick_greeting(edition: str, datum_iso: str, lang: str = "de") -> str:
    if lang == "en":
        pool = _GREETING_POOL_EN.get(edition, ["Your Briefing."])
    else:
        if datum_iso == "2026-06-15" and edition == "morgen":
            return "Guten Morgen, Andreas Rast."
        pool = _GREETING_POOL.get(edition, ["Dein Lagebild."])
    try:
        idx = date.fromisoformat(datum_iso).toordinal() % len(pool)
    except (ValueError, TypeError):
        idx = 0
    return pool[idx]


def _next_edition_hint(edition: str, lang: str = "de") -> str:
    """Dezente Rhythmus-Zeile für die Startseite (nächstes Lagebild + Takt)."""
    if edition not in _EDITION_ORDER:
        return ""
    i = _EDITION_ORDER.index(edition)
    nxt = _EDITION_ORDER[(i + 1) % len(_EDITION_ORDER)]
    if lang == "en":
        when = "tomorrow" if i == len(_EDITION_ORDER) - 1 else "today"
        return (
            '<p class="next-edition">'
            f"Next briefing: {when} at {_EDITION_TIME[nxt]} · "
            "Four editions daily: 6, 11, 16 &amp; 20:00"
            "</p>"
        )
    when = "morgen" if i == len(_EDITION_ORDER) - 1 else "heute"
    return (
        '<p class="next-edition">'
        f"Nächstes Lagebild: {when} {_EDITION_TIME[nxt]} Uhr · "
        "Die Presse kuratiert um 6, 11, 16 &amp; 20 Uhr"
        "</p>"
    )


def _timeline_panel(edition: str, lang: str = "de") -> str:
    """Richtung C: macht den Kuratierungs-Takt zum Helden.

    Horizontale 4-Knoten-Spur 06·11·16·20; vergangene Knoten gefüllt, der aktuelle
    hervorgehoben (blauer Halo), künftige hohl. Fortschrittsbalken bis zum aktuellen
    Knoten, Bildunterschrift mit dem nächsten Lagebild-Termin.
    """
    if edition not in _EDITION_ORDER:
        return ""
    cur = _EDITION_ORDER.index(edition)
    nodes = []
    for i, ed in enumerate(_EDITION_ORDER):
        label = _EDITION_TIME[ed][:2]
        cls = "tl-node now" if i == cur else ("tl-node done" if i < cur else "tl-node")
        nodes.append(f'<span class="{cls}">{label}</span>')
    fill = round(cur / (len(_EDITION_ORDER) - 1) * 100)
    nxt = _EDITION_ORDER[(cur + 1) % len(_EDITION_ORDER)]
    if lang == "en":
        when = "tomorrow" if cur == len(_EDITION_ORDER) - 1 else "today"
        tl_label = "Curated at"
        caption = f"Next update: <b>{when} at {_EDITION_TIME[nxt]}</b>"
    else:
        when = "morgen" if cur == len(_EDITION_ORDER) - 1 else "heute"
        tl_label = "Kuratiert um"
        caption = f"Nächste Aktualisierung: <b>{when} {_EDITION_TIME[nxt]} Uhr</b>"
    return (
        '<div class="timeline">'
        f'<div class="tl-label">{tl_label}</div>'
        '<div class="tl-track">'
        f'<span class="tl-fill" style="width:{fill}%"></span>'
        f'{"".join(nodes)}'
        "</div>"
        f'<p class="tl-caption">{caption}</p>'
        "</div>"
    )


def _lagebild_header(
    datum_iso: str, edition: str, points: int, lesezeit: int | None, lang: str = "de"
) -> str:
    """Baut den Seitenkopf: Kicker (Datum · Ausgabe), Begrüßung, Meta-Byline."""
    weekdays = _i18n.t(lang, "weekdays")
    months = _i18n.t(lang, "months")
    try:
        d = date.fromisoformat(datum_iso)
        if lang == "en":
            kicker = f"{weekdays[d.weekday()]}, {months[d.month - 1]} {d.day}, {d.year} · {_EDITION_LABEL_EN.get(edition, edition)}"
        else:
            kicker = f"{weekdays[d.weekday()]}, {d.day}. {months[d.month - 1]} · {_EDITION_LABEL.get(edition, edition)}"
    except (ValueError, TypeError):
        kicker = (_EDITION_LABEL_EN if lang == "en" else _EDITION_LABEL).get(edition, edition)
    greeting = _pick_greeting(edition, datum_iso, lang)
    byline = _NYT_BYLINE if lang == "en" else _BYLINE
    if lang == "en":
        meta = [byline]
        if points == 1:
            meta.append("1 story")
        elif points > 1:
            meta.append(f"{points} stories")
        if lesezeit and lesezeit < 90:
            meta.append(f"ca. {lesezeit} sec.")
        elif lesezeit:
            mins = round(lesezeit / 60 * 2) / 2
            label = f"{mins:.1f}".rstrip("0").rstrip(".")
            meta.append(f"ca. {label} min.")
    else:
        meta = [byline]
        if points == 1:
            meta.append("1 Thema")
        elif points > 1:
            meta.append(f"{points} Themen")
        if lesezeit and lesezeit < 90:
            meta.append(f"ca. {lesezeit} Sek.")
        elif lesezeit:
            mins = round(lesezeit / 60 * 2) / 2
            label = f"{mins:.1f}".rstrip("0").rstrip(".").replace(".", ",")
            meta.append(f"ca. {label} Min.")
    return (
        '<header class="lagebild-header">'
        f'<p class="kicker">{kicker}</p>'
        f"<h1>{greeting}</h1>"
        f'<p class="byline">{" · ".join(meta)}</p>'
        "</header>"
    )


def _add_article_feedback(content: str, datum: str, edition: str, lang: str = "de") -> str:
    """Fügt 👍/👎-Buttons nach jedem nummerierten Artikel ein."""
    content = re.sub(r'\n?<div class="article-fb".*?</div>', "", content)
    idx = 0
    less_label = "Less" if lang == "en" else "Weniger"

    def _insert(m: re.Match) -> str:
        nonlocal idx
        key = f"{datum}|{edition}|{idx}"
        idx += 1
        bar = (
            f'\n<div class="article-fb" data-key="{key}">'
            f'<button class="fb-btn" data-vote="up">Relevant</button>'
            f'<button class="fb-btn" data-vote="down">{less_label}</button>'
            f"</div>"
        )
        return m.group(0).rstrip() + bar

    return re.sub(r"<h2>(?!Deine Themen|Your Topics).*?(?=<h2>|<hr>)", _insert, content, flags=re.DOTALL)


def _enhance_content(content: str, datum: str = "", edition: str = "", lang: str = "de") -> str:
    """Verleiht dem Roh-Inhalt Die-Presse-/NYT-Charakter (Pills, Kicker, Highlight-Box)."""
    content = re.sub(
        r'<div class="audio-player">.*?</div>\s*', "", content, flags=re.DOTALL
    )
    content = re.sub(
        r'<(p|div)[^>]*class="brand"[^>]*>.*?</\1>\s*', "", content, flags=re.DOTALL
    )
    # Meta-Klammer — Bericht:/By: als Ressort-Pill + Quellenzeile
    if 'class="ressort"' not in content:
        if lang == "en":
            content = re.sub(
                r'\(([^)]{2,60})\)\s*(?=<a[^>]*>→ Article</a>)', _meta_tag_en, content
            )
        else:
            content = re.sub(
                r'\(([^)]{2,60})\)\s*(?=<a[^>]*>→ Artikel</a>)', _meta_tag, content
            )
    # Nummerierte Emojis + optionale Topic-Emojis am Anfang von h2-Titeln entfernen
    content = re.sub(
        r'(<h2>)\s*\d[^\w\s]*\s*(?:[^\x00-\x7F]\S*\s*)?',
        r'\1',
        content,
    )
    # Nummern-Emojis aus "Heute wichtig"/"Today's headlines"-Einträgen entfernen
    content = re.sub(
        r'(<div class="highlights">)(.*?)(</div>)',
        lambda m: m.group(1)
            + re.sub(r'\d️?⃣?\s*', '', m.group(2))
            + m.group(3),
        content,
        flags=re.DOTALL,
    )
    # Quell-Links als Pill auszeichnen (sprachspezifischer Link-Text)
    if lang == "en":
        content = re.sub(
            r'<a href="([^"]+)">→ Article</a>',
            r'<a class="source-link" href="\1">Read in the NYT →</a>',
            content,
        )
    else:
        content = re.sub(
            r'<a href="([^"]+)">→ Artikel</a>',
            r'<a class="source-link" href="\1">Weiterlesen bei der Presse →</a>',
            content,
        )
    # E-Paper-Paragraph (📰) entfernen — steht bereits in der Tab-Leiste.
    content = re.sub(r'\s*<p>[^<]*📰.*?</p>', '', content, flags=re.DOTALL)
    # Done-Box: Emoji und ungültige <em>-Tags bereinigen.
    content = re.sub(
        r'<div class="done">[^<]*<em>(.*?)(?:</em>)?</div>',
        r'<div class="done"><span class="done-check">✓</span> \1</div>',
        content, flags=re.DOTALL,
    )
    content = re.sub(
        r'<div class="done">[✅\s]*(.*?)</div>',
        r'<div class="done"><span class="done-check">✓</span> \1</div>',
        content, flags=re.DOTALL,
    )
    # Topic-Sektionsköpfe: kein Accordion
    if lang == "en":
        content = content.replace(
            '<h2>Your Topics</h2>',
            '<h2 class="topic-summary-head">Your Topics</h2>',
        )
    else:
        content = content.replace(
            '<h2>Deine Themen</h2>',
            '<h2 class="topic-summary-head">Deine Themen</h2>',
        )
    # Seitenkopf neu bauen
    if datum:
        points = len(re.findall(r"<h2>\s*[1-9]", content))
        if lang == "en":
            m = re.search(r"reading time ca\.\s*(\d+)\s*seconds", content)
        else:
            m = re.search(r"Lesezeit ca\.\s*(\d+)\s*Sekunden", content)
        lesezeit = int(m.group(1)) if m else None
        header = _lagebild_header(datum, edition, points, lesezeit, lang)
        if '<header class="lagebild-header">' in content:
            content = re.sub(
                r'<header class="lagebild-header">.*?</header>',
                header, content, count=1, flags=re.DOTALL,
            )
        else:
            content = re.sub(
                r'<h1>.*?</h1>\s*(?:<p class="byline">.*?</p>\s*)?',
                header, content, count=1, flags=re.DOTALL,
            )
    else:
        byline = _NYT_BYLINE if lang == "en" else _BYLINE
        content = re.sub(
            r'<p class="byline">.*?</p>',
            f'<p class="byline">{byline}</p>', content, count=1, flags=re.DOTALL,
        )
        if 'class="byline"' not in content:
            content = re.sub(
                r"(</h1>)", rf'\1\n<p class="byline">{byline}</p>', content, count=1
            )
    # Redakteur:innen-Fußzeile als eigene Klasse auszeichnen
    if lang == "en":
        content = re.sub(
            r'<p><em>(Today&#x27;s reporting by:.*?|Today\'s reporting by:.*?)</em></p>',
            r'<p class="reporters">\1</p>', content, count=1, flags=re.DOTALL,
        )
    else:
        content = re.sub(
            r'<p><em>(Heute mit Berichterstattung von:.*?)</em></p>',
            r'<p class="reporters">\1</p>', content, count=1, flags=re.DOTALL,
        )
    # „Heute wichtig" / „Today's headlines" + die nummerierten Zeilen zu einer Highlight-Box bündeln.
    if 'class="highlights"' not in content:
        if lang == "en":
            content = re.sub(
                r'(<p><strong>Today&#x27;s headlines:</strong></p>.*?)(?=<hr>)',
                r'<div class="highlights">\1</div>',
                content, count=1, flags=re.DOTALL,
            )
        else:
            content = re.sub(
                r'(<p><strong>Heute wichtig:</strong></p>.*?)(?=<hr>)',
                r'<div class="highlights">\1</div>',
                content, count=1, flags=re.DOTALL,
            )
    if datum:
        content = _add_article_feedback(content, datum, edition, lang)
    return content.strip()


def _extract_body(html: str, datum: str = "", edition: str = "", lang: str = "de") -> str:
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
                return _enhance_content(html[content_start:c].strip(), datum, edition, lang)
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


def _label(d: date, edition: str, lang: str = "de") -> str:
    weekdays = _i18n.t(lang, "weekdays")
    months = _i18n.t(lang, "months")
    if lang == "en":
        ed_label = _EDITION_LABEL_EN.get(edition, edition)
        return f"{weekdays[d.weekday()]}, {months[d.month - 1]} {d.day} · {ed_label}"
    return f"{weekdays[d.weekday()]} {d.day}. {months[d.month - 1]} · {_EDITION_LABEL[edition]}"


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
            f'<a href="{_html.escape(a["link"])}" target="_blank" rel="noopener">'
            f'<span class="topic-article-title">{_html.escape(a["title"])}</span>'
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

    topic_cards = "\n".join(_topic_card_html(t, dossier, topic_articles) for t in topics)
    if not topic_cards:
        topic_cards = '<p class="empty-state">Keine Themen konfiguriert.</p>'

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
  <p class="as-intro-text">Wähle die Themen aus, über die du regelmäßig informiert werden möchtest. Die Fragen helfen dir einzuschätzen, was für dich relevant ist.</p>
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
var PREF_KEY='copilot_prefs';
var CUSTOM_KEY='copilot_custom';
var OLD_PREF_KEY='auf_stand_prefs';
var OLD_CUSTOM_KEY='auf_stand_custom';
if(!localStorage.getItem(PREF_KEY) && localStorage.getItem(OLD_PREF_KEY)){{
  localStorage.setItem(PREF_KEY, localStorage.getItem(OLD_PREF_KEY));
}}
if(!localStorage.getItem(CUSTOM_KEY) && localStorage.getItem(OLD_CUSTOM_KEY)){{
  localStorage.setItem(CUSTOM_KEY, localStorage.getItem(OLD_CUSTOM_KEY));
}}
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

try{{
  var saved=JSON.parse(localStorage.getItem(PREF_KEY)||'null');
  customTopics=JSON.parse(localStorage.getItem(CUSTOM_KEY)||'[]');
  if(saved&&saved.length){{show('topic-list');filterTopics(saved);}}
  else{{show('as-intro');}}
}}catch(e){{show('as-intro');}}

window.asOpen=function(){{
  try{{
    var saved=JSON.parse(localStorage.getItem(PREF_KEY)||'[]');
    selected=new Set(saved||[]);
  }}catch(e){{selected=new Set();}}
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

    content = "<h1>Meine Themen</h1>\n" + assessment_html + _PUSH_SECTION
    html = _render_page("Meine Themen", content, "dossier")
    (SITE_DIR / "dossier.html").write_text(html, encoding="utf-8")


def _build_nyt_dossier(site_dir: Path, state: dict, topics: list, config: dict) -> None:
    """Erzeugt site/nyt/dossier.html (englische Topics-Seite)."""
    from .synthesize import topic_keyword, topic_name as get_topic_name
    site_dir.mkdir(parents=True, exist_ok=True)
    epaper_url = config.get("epaper_url", "https://www.nytimes.com/section/todayspaper")

    dossier = state.get("dossier", {})
    topic_articles = state.get("topic_articles", {})

    def topic_card_en(topic) -> str:
        name = get_topic_name(topic)
        kw = topic_keyword(topic)
        badge = f'<span class="schlagwort-badge">#{kw}</span>' if kw else ""
        arts = topic_articles.get(name, [])
        if arts:
            items = "\n".join(
                f'<li class="topic-article">'
                f'<a href="{_html.escape(a["link"])}" target="_blank" rel="noopener">'
                f'<span class="topic-article-title">{_html.escape(a["title"])}</span>'
                f'<span class="topic-article-date">{_iso_to_display(a["date"])[:5]}</span>'
                f"</a></li>"
                for a in arts if a.get("link") and a.get("title")
            )
            body_html = f'<ul class="topic-articles">{items}</ul>'
        else:
            body_html = '<p class="dossier-empty">No recent articles on this topic.</p>'
        return (
            f'<div class="dossier-topic" data-topic-name="{_html.escape(name)}">'
            f"<h2>{_html.escape(name)}{badge}</h2>"
            f"{body_html}"
            f"</div>"
        )

    topic_cards = "\n".join(topic_card_en(t) for t in topics)
    if not topic_cards:
        topic_cards = '<p class="empty-state">No topics configured.</p>'

    topics_data = [
        {
            "name": get_topic_name(t),
            "kw": topic_keyword(t),
            "q": t.get("assessment_question", "") if isinstance(t, dict) else "",
        }
        for t in topics
        if isinstance(t, dict) and t.get("assessment_question")
    ]
    topics_js = json.dumps(topics_data, ensure_ascii=False)

    toggle_cards_html = "\n".join(
        f'<div class="as-toggle-card" data-name="{_html.escape(td["name"])}" onclick="asToggle(this)">'
        f'<div class="as-card-check">✓</div>'
        f'<div><div class="as-card-name">{_html.escape(td["name"])}</div>'
        f'<div class="as-card-q">{_html.escape(td["q"])}</div></div>'
        f"</div>"
        for td in topics_data
    )

    content = f"""<h1>My Topics</h1>
<div id="as-intro">
  <p class="as-intro-text">Select the topics you want to follow. The questions help you gauge what's relevant to you.</p>
  <button class="as-btn-primary" onclick="asOpen()">Select topics →</button>
</div>
<div id="as-cards" style="display:none">
  <p style="font-size:13px;color:var(--muted);font-family:var(--sans);margin:0 0 16px">Tap a topic to select or deselect it.</p>
  {toggle_cards_html}
  <div class="as-confirm-row">
    <span id="as-count" style="font-size:13px;color:var(--muted);font-family:var(--sans)">0 selected</span>
    <button class="as-btn-primary" onclick="asConfirm()">Save</button>
  </div>
</div>
<div id="topic-list" style="display:none">
{topic_cards}
  <button class="reset-link" onclick="asReset()">Edit topic selection</button>
</div>
<script>
(function(){{
var TOPICS={topics_js};
var PREF_KEY='nyt_prefs';
var selected=new Set();
function show(id){{['as-intro','as-cards','topic-list'].forEach(function(i){{
  document.getElementById(i).style.display=i===id?'':'none';
}});}}
function filterTopics(prefs){{
  document.getElementById('topic-list').querySelectorAll('.dossier-topic').forEach(function(el){{
    el.style.display=(!prefs||prefs.indexOf(el.dataset.topicName)>=0)?'':'none';
  }});
}}
function updateCount(){{
  document.getElementById('as-count').textContent=selected.size+' selected';
}}
try{{
  var saved=JSON.parse(localStorage.getItem(PREF_KEY)||'null');
  if(saved&&saved.length){{show('topic-list');filterTopics(saved);}}
  else{{show('as-intro');}}
}}catch(e){{show('as-intro');}}
window.asOpen=function(){{
  try{{selected=new Set(JSON.parse(localStorage.getItem(PREF_KEY)||'[]'));}}
  catch(e){{selected=new Set();}}
  document.querySelectorAll('.as-toggle-card').forEach(function(el){{
    el.classList.toggle('selected',selected.has(el.dataset.name));
  }});
  updateCount();show('as-cards');
}};
window.asToggle=function(el){{
  var name=el.dataset.name;
  if(selected.has(name)){{selected.delete(name);el.classList.remove('selected');}}
  else{{selected.add(name);el.classList.add('selected');}}
  updateCount();
}};
window.asConfirm=function(){{
  localStorage.setItem(PREF_KEY,JSON.stringify(Array.from(selected)));
  show('topic-list');filterTopics(Array.from(selected));
}};
window.asReset=function(){{window.asOpen();}};
}})();
</script>"""

    html = _render_nyt_page("My Topics", content, "dossier", epaper_url=epaper_url)
    (site_dir / "dossier.html").write_text(html, encoding="utf-8")


# Push-Aktivierung — eigenständiger Block am Ende des Themen-Screens.
_PUSH_SECTION = """
<div id="push-section" style="display:none;border-top:1px solid var(--border);padding-top:24px;margin-top:36px">
  <p style="font-size:15px;font-weight:600;font-family:var(--sans);margin:0 0 4px">🔔 Push-Benachrichtigungen</p>
  <p style="font-size:13px;color:var(--muted);font-family:var(--sans);margin:0 0 14px;line-height:1.6">
    Lass dich benachrichtigen, sobald ein neues Lagebild da ist — direkt aufs Gerät,
    ohne die App zu öffnen. (Auf dem iPhone zuerst „Zum Home-Bildschirm" hinzufügen.)
  </p>
  <button class="as-btn-primary" id="push-enable" onclick="pushEnable()">Benachrichtigungen aktivieren</button>
  <div id="push-cmd-wrap" style="display:none;margin-top:16px">
    <p style="font-size:13px;color:var(--muted);font-family:var(--sans);margin:0 0 6px">
      Fast geschafft: Sende diesen Code an deinen Telegram-Bot, um Push zu bestätigen.
    </p>
    <div class="as-cmd-box" id="push-cmd-text"></div>
    <button class="tg-copy-btn" onclick="pushCopyCmd()">Kopieren</button>
  </div>
  <p id="push-msg" style="font-size:13px;font-family:var(--sans);margin:12px 0 0;color:var(--accent)"></p>
</div>

<script>
(function(){
  var section=document.getElementById('push-section');
  if(!('serviceWorker' in navigator)||!('PushManager' in window)||!window.VAPID_PUBLIC_KEY){
    return;
  }
  section.style.display='';

  function urlB64ToUint8(base64){
    var pad='='.repeat((4-base64.length%4)%4);
    var b=(base64+pad).replace(/-/g,'+').replace(/_/g,'/');
    var raw=atob(b),arr=new Uint8Array(raw.length);
    for(var i=0;i<raw.length;i++)arr[i]=raw.charCodeAt(i);
    return arr;
  }

  window.pushEnable=function(){
    var msg=document.getElementById('push-msg');
    Notification.requestPermission().then(function(perm){
      if(perm!=='granted'){msg.textContent='Benachrichtigungen wurden nicht erlaubt.';return;}
      return navigator.serviceWorker.ready.then(function(reg){
        return reg.pushManager.getSubscription().then(function(existing){
          return existing||reg.pushManager.subscribe({
            userVisibleOnly:true,
            applicationServerKey:urlB64ToUint8(window.VAPID_PUBLIC_KEY)
          });
        });
      }).then(function(sub){
        var blob=btoa(JSON.stringify(sub)).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');
        document.getElementById('push-cmd-text').textContent='/push '+blob;
        document.getElementById('push-cmd-wrap').style.display='';
        msg.textContent='';
      });
    }).catch(function(e){msg.textContent='Aktivierung fehlgeschlagen: '+e.message;});
  };

  window.pushCopyCmd=function(){
    var t=document.getElementById('push-cmd-text').textContent;
    navigator.clipboard&&navigator.clipboard.writeText(t).then(function(){
      var b=document.querySelector('#push-cmd-wrap .tg-copy-btn');
      b.textContent='✓ Kopiert';setTimeout(function(){b.textContent='Kopieren';},2000);
    });
  };
})();
</script>
"""


def build_archiv_index(editions: list, lang: str = "de", site_dir: Path | None = None,
                       epaper_url: str = "https://www.diepresse.com/epaper") -> None:
    """Erzeugt archiv/index.html als Karten-Raster."""
    _site = site_dir or SITE_DIR
    _archiv = _site / "archiv"
    _archiv.mkdir(parents=True, exist_ok=True)
    cards = "\n".join(
        f'<a class="archiv-card" href="{path.name}">'
        f'<span class="archiv-date">{_label(d, edition, lang)}</span>'
        f'<span class="archiv-label">{(_EDITION_LABEL_EN if lang == "en" else _EDITION_LABEL)[edition]}</span>'
        f"</a>"
        for (d, _rank, edition), path in editions[:60]
    )
    title = "Archive" if lang == "en" else "Archiv"
    content = f'<h1>{title}</h1>\n<div class="archiv-grid">\n{cards}\n</div>'
    if lang == "en":
        html = _render_nyt_page(title, content, "archiv", root="../", epaper_url=epaper_url)
    else:
        html = _render_page(title, content, "archiv", root="../")
    (_archiv / "index.html").write_text(html, encoding="utf-8")


_MANIFEST = {
    "name": "Copilot · Die Presse",
    "short_name": "Copilot",
    "description": "Dein tägliches Lagebild der Presse — in rund 90 Sekunden informiert.",
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

_NYT_MANIFEST = {
    "name": "NYT Briefing · Copilot",
    "short_name": "NYT Briefing",
    "description": "Your daily NYT briefing — informed in 90 seconds.",
    "lang": "en",
    "dir": "ltr",
    "start_url": "./index.html",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait",
    "background_color": "#ffffff",
    "theme_color": "#ffffff",
    "categories": ["news"],
    "icons": [
        {"src": "../icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "../icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        {"src": "../icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
    ],
}

_SERVICE_WORKER = """\
const CACHE = 'copilot-v2';
const SHELL = ['./', './index.html', './dossier.html', './archiv/index.html',
  './icon-192.png', './icon-512.png', './apple-touch-icon.png', './die-presse-logo.png'];

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

self.addEventListener('push', function(e){
  var d = {};
  try { d = e.data.json(); } catch(err){}
  e.waitUntil(self.registration.showNotification(d.title || 'Copilot', {
    body: d.body || '', icon: './icon-192.png', badge: './icon-192.png',
    data: { url: d.url || './index.html' }, tag: 'lagebild'
  }));
});

self.addEventListener('notificationclick', function(e){
  e.notification.close();
  var target = (e.notification.data && e.notification.data.url) || './index.html';
  e.waitUntil(clients.matchAll({type:'window'}).then(function(list){
    for(var i=0;i<list.length;i++){ if('focus' in list[i]) return list[i].focus(); }
    if(clients.openWindow) return clients.openWindow(target);
  }));
});
"""

_NYT_SERVICE_WORKER = _SERVICE_WORKER.replace(
    "const CACHE = 'copilot-v2';",
    "const CACHE = 'nyt-briefing-v1';"
).replace(
    "const SHELL = ['./', './index.html', './dossier.html', './archiv/index.html',\n"
    "  './icon-192.png', './icon-512.png', './apple-touch-icon.png', './die-presse-logo.png'];",
    "const SHELL = ['./', './index.html', './dossier.html', './archiv/index.html'];"
).replace(
    "tag: 'lagebild'",
    "tag: 'nyt-briefing'"
)


def _write_pwa_assets(site_dir: Path | None = None, manifest: dict | None = None,
                      sw: str | None = None) -> None:
    """Schreibt Web-App-Manifest, Service Worker und Push-Config."""
    import os
    _site = site_dir or SITE_DIR
    _site.mkdir(parents=True, exist_ok=True)
    _manifest = manifest or _MANIFEST
    (_site / "manifest.webmanifest").write_text(
        json.dumps(_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (_site / "sw.js").write_text(sw or _SERVICE_WORKER, encoding="utf-8")
    vapid_public = os.environ.get("VAPID_PUBLIC_KEY", "")
    (_site / "push-config.js").write_text(
        f'window.VAPID_PUBLIC_KEY = "{vapid_public}";\n', encoding="utf-8"
    )


def _audio_player(src: str) -> str:
    return (
        '<div class="audio-player">'
        '<span class="audio-label">▶ Lagebild zum Hören</span>'
        f'<audio controls preload="none" src="{src}"></audio>'
        "</div>\n"
    )


def _insert_after_header(content: str, snippet: str) -> str:
    if "</header>" in content:
        return content.replace("</header>", snippet + "\n</header>", 1)
    if "</h1>" in content:
        return content.replace("</h1>", "</h1>\n" + snippet, 1)
    return snippet + content


def _prune_old_audio(archiv_dir: Path, days: int = 14) -> None:
    """Löscht mp3-Dateien im Archiv, die älter als `days` Tage sind."""
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=days)
    for mp3 in archiv_dir.glob("*.mp3"):
        m = re.match(rf"^(\d{{4}})-(\d{{2}})-(\d{{2}})-({_EDITIONS_RE})\.mp3$", mp3.name)
        if not m:
            continue
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if d < cutoff:
            mp3.unlink()


def _build_presse_site() -> Path:
    """Baut die deutsche Presse-Edition (site/)."""
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

    out_dir = _render.OUT_DIR
    archiv_dir = ARCHIV_DIR
    archiv_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.exists():
        for path in out_dir.glob("*.html"):
            if _parse(path):
                shutil.copy2(path, archiv_dir / path.name)
        for mp3 in out_dir.glob("*.mp3"):
            if re.match(rf"^\d{{4}}-\d{{2}}-\d{{2}}-({_EDITIONS_RE})\.mp3$", mp3.name):
                shutil.copy2(mp3, archiv_dir / mp3.name)
    _prune_old_audio(archiv_dir)

    editions = [
        (parsed, path)
        for path in archiv_dir.glob("*.html")
        if (parsed := _parse(path))
    ]
    index = SITE_DIR / "index.html"
    if not editions:
        print("Keine Ausgaben im Archiv — index.html bleibt unverändert.")
        return index

    editions.sort(key=lambda e: e[0], reverse=True)

    for (d, _rank, edition), path in editions:
        raw = path.read_text(encoding="utf-8")
        content = _extract_body(raw, d.isoformat(), edition, "de")
        mp3_name = f"{d.isoformat()}-{edition}.mp3"
        if (archiv_dir / mp3_name).exists():
            content = _insert_after_header(content, _audio_player(mp3_name))
        branded = _render_page(_label(d, edition, "de"), content, "archiv", root="../")
        path.write_text(branded, encoding="utf-8")

    build_archiv_index(editions)

    latest_html = editions[0][1].read_text(encoding="utf-8")
    latest_d, _, latest_edition = editions[0][0]
    latest_content = _extract_body(latest_html, latest_d.isoformat(), latest_edition, "de")
    latest_mp3 = f"{latest_d.isoformat()}-{latest_edition}.mp3"
    if (archiv_dir / latest_mp3).exists():
        latest_content = _insert_after_header(
            latest_content, _audio_player(f"archiv/{latest_mp3}")
        )
    from . import state as state_mod
    streak = state_mod.current_streak(state)
    if streak >= 2:
        latest_content = _insert_after_header(
            latest_content,
            f'<div class="streak">🔥 {streak} Tage in Folge informiert</div>\n',
        )
    timeline = _timeline_panel(latest_edition, "de")
    if timeline:
        latest_content = _insert_after_header(latest_content, timeline)
    else:
        hint = _next_edition_hint(latest_edition, "de")
        if hint:
            latest_content = _insert_after_header(latest_content, hint)

    title = _label(latest_d, latest_edition, "de")
    index_html = _render_page(title, latest_content, "lagebild")
    index.write_text(index_html, encoding="utf-8")

    print(f"Web-App gebaut: {index} ({len(editions)} Ausgabe(n) im Archiv)")
    return index


def _build_nyt_site(config: dict) -> Path:
    """Baut die englische NYT-Edition (site/nyt/)."""
    site_dir = BASE_DIR / config.get("site_dir", "site/nyt")
    archiv_dir = site_dir / "archiv"
    state_path = BASE_DIR / config.get("state_file", "data/state.nyt.json")
    out_dir = BASE_DIR / config.get("out_dir", "out/nyt")
    epaper_url = config.get("epaper_url", "https://www.nytimes.com/section/todayspaper")
    lang = "en"

    state: dict = {}
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    _write_pwa_assets(site_dir, _NYT_MANIFEST, _NYT_SERVICE_WORKER)
    all_topics = config.get("topics", []) + state.get("custom_topics", [])
    _build_nyt_dossier(site_dir, state, all_topics, config)

    archiv_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.exists():
        for path in out_dir.glob("*.html"):
            if _parse(path):
                shutil.copy2(path, archiv_dir / path.name)
        for mp3 in out_dir.glob("*.mp3"):
            if re.match(rf"^\d{{4}}-\d{{2}}-\d{{2}}-({_EDITIONS_RE})\.mp3$", mp3.name):
                shutil.copy2(mp3, archiv_dir / mp3.name)
    _prune_old_audio(archiv_dir)

    editions = [
        (parsed, path)
        for path in archiv_dir.glob("*.html")
        if (parsed := _parse(path))
    ]
    index = site_dir / "index.html"
    if not editions:
        print("No NYT editions in archive — index.html unchanged.")
        return index

    editions.sort(key=lambda e: e[0], reverse=True)

    for (d, _rank, edition), path in editions:
        raw = path.read_text(encoding="utf-8")
        content = _extract_body(raw, d.isoformat(), edition, lang)
        branded = _render_nyt_page(
            _label(d, edition, lang), content, "archiv", root="../", epaper_url=epaper_url
        )
        path.write_text(branded, encoding="utf-8")

    build_archiv_index(editions, lang=lang, site_dir=site_dir, epaper_url=epaper_url)

    latest_html = editions[0][1].read_text(encoding="utf-8")
    latest_d, _, latest_edition = editions[0][0]
    latest_content = _extract_body(latest_html, latest_d.isoformat(), latest_edition, lang)
    timeline = _timeline_panel(latest_edition, lang)
    if timeline:
        latest_content = _insert_after_header(latest_content, timeline)
    else:
        hint = _next_edition_hint(latest_edition, lang)
        if hint:
            latest_content = _insert_after_header(latest_content, hint)

    title = _label(latest_d, latest_edition, lang)
    index_html = _render_nyt_page(title, latest_content, "lagebild", epaper_url=epaper_url)
    index.write_text(index_html, encoding="utf-8")

    print(f"NYT site built: {index} ({len(editions)} edition(s) in archive)")
    return index


def build_site(config: dict | None = None) -> Path:
    """Kopiert neue Ausgaben ins Archiv und baut alle Site-Seiten neu.

    config=None oder language='de' → Presse-Edition (site/).
    language='en' → NYT-Edition (site/nyt/).
    """
    lang = (config or {}).get("language", "de")
    if lang == "en" and config:
        return _build_nyt_site(config)
    return _build_presse_site()
