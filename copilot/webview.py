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

_EDITION_RANK = {"catchup": 0, "morgen": 1, "mittag": 2, "nachmittag": 3, "abend": 4}
_EDITION_LABEL = {
    "morgen": "Morgen-Ausgabe", "mittag": "Mittags-Ausgabe",
    "nachmittag": "Nachmittags-Ausgabe", "abend": "Abend-Ausgabe",
    "catchup": "Catch-up",
}
# Presse-Kuratierungszeiten je Ausgabe (für die dezente Rhythmus-Anzeige).
_EDITION_TIME = {"morgen": "06:00", "mittag": "11:00", "nachmittag": "16:00", "abend": "20:00"}
_EDITION_ORDER = ["morgen", "mittag", "nachmittag", "abend"]
_EDITIONS_RE = "morgen|mittag|nachmittag|abend|catchup"
_FILENAME_RE = re.compile(rf"^(\d{{4}})-(\d{{2}})-(\d{{2}})-({_EDITIONS_RE})\.html$")

# ---------------------------------------------------------------------------
# Design-System — Die Presse · Copilot (Dark, im Look der echten App)
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
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;1,8..60,500&family=Libre+Franklin:wght@400;500;600;700&display=swap" rel="stylesheet">
  <title>__TITLE__ · Die Presse · Copilot</title>
  <style>
    /* Copilot · Die Presse — Design B (Modern Clean)
       Schriften: Source Serif 4 (Headlines), Libre Franklin (UI + Text).
       Akzent: #1e5fd6 (Presse-Blau). Hintergrund: #eef1f5 mit weißen Karten. */
    :root {
      --bg: #eef1f5; --surface: #ffffff; --border: #e6eaf0;
      --text: #16202b; --fg: #3a444f; --muted: #7c8aa0;
      --accent: #1e5fd6; --accent-soft: rgba(30,95,214,.10);
      --accent-shadow: rgba(30,95,214,.50);
      --serif: 'Source Serif 4', Georgia, 'Times New Roman', serif;
      --sans: 'Libre Franklin', -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { height: -webkit-fill-available; }
    body {
      background: #dfe3e8; color: var(--text); font-family: var(--sans);
      -webkit-font-smoothing: antialiased;
      display: flex; flex-direction: column;
      height: 100vh; height: -webkit-fill-available; overflow: hidden;
    }
    /* ── App-Shell (zentrierte Handy-Säule) ── */
    .app {
      max-width: 430px; width: 100%; margin: 0 auto; background: var(--bg);
      display: flex; flex-direction: column;
      height: 100vh; height: -webkit-fill-available; overflow: hidden;
    }
    /* ── Scroll-Bereich ── */
    .scroll-area { flex: 1; overflow-y: auto; -webkit-overflow-scrolling: touch; }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    /* ── Topbar (ersetzt Masthead) ── */
    .topbar {
      background: var(--surface); box-shadow: 0 1px 0 var(--border);
      flex-shrink: 0;
    }
    .brandrow {
      display: flex; align-items: center; justify-content: space-between;
      padding: 10px 22px 14px;
    }
    .wordmark-text {
      font-family: var(--serif); font-weight: 700; font-size: 19px;
      letter-spacing: -.01em; color: var(--text);
    }
    .copilot-pill {
      display: inline-flex; align-items: center; padding: 5px 11px;
      border-radius: 999px; font: 700 10px var(--sans);
      letter-spacing: .1em; text-transform: uppercase;
      background: var(--accent-soft); color: var(--accent);
    }
    .progress-track { height: 2px; background: var(--bg); }
    .progress-bar {
      height: 100%; border-radius: 0 2px 2px 0;
      background: var(--accent); width: 0; transition: width .12s linear;
    }
    /* ── Masthead ausblenden (Topbar übernimmt) ── */
    .masthead { display: none; }
    /* ── Layout ── */
    .wrap { padding: 6px 0 16px; }
    /* ── Typografie ── */
    h1 {
      font-family: var(--serif); font-size: 1.9rem; line-height: 1.14;
      margin: 0 0 12px; font-weight: 600; color: var(--text); letter-spacing: -.015em;
    }
    h2 {
      font-family: var(--serif); font-size: 1.25rem; line-height: 1.25;
      margin: 0 0 10px; font-weight: 600; color: var(--text);
    }
    p { margin: 0 0 13px; color: var(--fg); font-size: 15px; line-height: 1.6; }
    strong {
      font-family: var(--sans); font-size: 10.5px; letter-spacing: .08em;
      text-transform: uppercase; color: var(--accent); font-weight: 700;
    }
    em { font-style: italic; color: var(--muted); }
    hr { border: none; border-top: 1px solid var(--border); margin: 0; }
    /* ── Lagebild-Kopf als Karte ── */
    .lagebild-header {
      background: var(--surface); border-radius: 18px; padding: 20px;
      margin: 8px 16px 6px; box-shadow: 0 10px 28px -16px rgba(22,32,43,.28);
    }
    .kicker {
      font: 600 11px var(--sans); letter-spacing: .04em; text-transform: uppercase;
      color: var(--accent); margin: 0 0 10px;
    }
    .lagebild-header h1 { margin: 0 0 12px; }
    .next-edition { font: 400 12px var(--sans); color: var(--muted); margin: 8px 0 0; }
    /* ── Byline ── */
    .byline {
      font: 500 13px var(--sans); color: var(--muted);
      padding-top: 10px; border-top: 1px solid var(--border); margin: 10px 0 0;
    }
    /* ── Streak ── */
    .streak {
      display: inline-flex; align-items: center; gap: 6px;
      font: 600 12px var(--sans); color: #c47d1a;
      background: #fff3e0; border-radius: 999px;
      padding: 5px 13px; margin: 10px 0 0;
    }
    /* ── Audio-Player ── */
    .audio-player {
      background: var(--surface); border-radius: 14px; padding: 16px 18px;
      margin: 6px 16px; box-shadow: 0 8px 20px -14px rgba(22,32,43,.22);
    }
    .audio-player .audio-label {
      display: block; font: 600 11px var(--sans); letter-spacing: .08em;
      text-transform: uppercase; color: var(--muted); margin-bottom: 8px;
    }
    .audio-player audio { width: 100%; height: 40px; }
    /* ── Heute-wichtig-Box als Karte ── */
    .highlights {
      background: var(--surface); border-radius: 18px; padding: 18px 20px;
      margin: 6px 16px; box-shadow: 0 10px 28px -16px rgba(22,32,43,.28);
    }
    .highlights strong { display: block; margin-bottom: 10px; }
    .highlights p { margin: 0 0 7px; font-size: 14px; line-height: 1.45; color: var(--fg); }
    .highlights p:last-child { margin-bottom: 0; }
    /* ── Story-Karten (h2 + Body bis zur nächsten hr) ── */
    .story-card {
      background: var(--surface); border-radius: 18px; padding: 18px 20px 16px;
      margin: 6px 16px; box-shadow: 0 10px 28px -16px rgba(22,32,43,.28);
    }
    /* Fallback: h2 außerhalb story-card (dossier/archiv) */
    h2 { margin: 28px 0 10px; }
    /* ── Accordion (Story-Karten) ── */
    .story-head {
      display: flex; gap: 12px; align-items: flex-start;
      cursor: pointer; padding: 0 0 14px;
    }
    .story-head h2 { flex: 1; margin: 0; padding: 0; }
    .story-head .chev {
      flex: none; width: 27px; height: 27px; border-radius: 50%;
      background: #f1f4f8; color: #7c8aa0;
      font-family: var(--serif); font-size: 17px;
      display: flex; align-items: center; justify-content: center;
      line-height: 1; flex-shrink: 0; margin-top: 2px;
    }
    .story-body { max-height: 0; opacity: 0; overflow: hidden;
      transition: max-height .3s ease, opacity .2s ease; }
    .story-card.open .story-body { max-height: 2000px; opacity: 1;
      transition: max-height .45s ease, opacity .35s ease; }
    .story-card { padding: 18px 20px 16px; }
    /* ── „Was ist neu / Warum es zählt" als Kicker-Label über dem Text ── */
    .story-body p > strong:first-child {
      display: block; margin-bottom: 4px; font-size: 10px; letter-spacing: .1em;
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
      margin: 6px 16px 0; padding-top: 14px; border-top: 1px solid var(--border);
    }
    /* ── Done-Box ── */
    .done {
      background: var(--surface); border-radius: 18px; padding: 16px 20px;
      margin: 6px 16px; box-shadow: 0 10px 28px -16px rgba(22,32,43,.28);
      font: 600 13px var(--sans); color: #1f8a5b;
    }
    /* ── Archiv ── */
    .archiv-grid {
      display: flex; flex-direction: column; gap: 8px;
      margin: 8px 16px 0;
    }
    .archiv-card {
      display: block; background: var(--surface); border-radius: 14px;
      padding: 15px 18px; box-shadow: 0 8px 22px -14px rgba(22,32,43,.25);
      border: 1.5px solid var(--border); transition: border-color .15s;
    }
    .archiv-card:hover { border-color: var(--accent); text-decoration: none; }
    .archiv-date { display: block; font: 600 14px var(--sans); color: var(--text); margin-bottom: 3px; }
    .archiv-label { display: block; font: 400 12px var(--sans); color: var(--muted); }
    /* ── Dossier / Themen ── */
    .dossier-topic {
      background: var(--surface); border-radius: 14px; padding: 18px 20px;
      margin: 6px 16px; box-shadow: 0 8px 22px -14px rgba(22,32,43,.25);
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
    /* ── Tab-Leiste (sticky unten) ── */
    .tabbar {
      background: var(--surface); border-top: 1px solid var(--border);
      display: flex; z-index: 20; padding: 8px 4px;
      padding-bottom: calc(10px + env(safe-area-inset-bottom));
      flex-shrink: 0;
    }
    .tab {
      flex: 1; display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 3px; color: var(--muted);
      font: 500 10px var(--sans); letter-spacing: .02em; text-transform: uppercase;
      transition: color .15s; border-top: 2px solid transparent; padding-top: 6px;
    }
    .tab:hover { color: var(--text); text-decoration: none; }
    .tab svg { width: 22px; height: 22px; }
    .tab.active { color: var(--accent); font-weight: 700; border-top-color: var(--accent); }
    /* ── Artikel-Feedback ── */
    .article-fb { display: flex; gap: 8px; margin: 12px 0 4px; flex-wrap: wrap; }
    .fb-btn {
      display: inline-flex; align-items: center; gap: 5px;
      background: #eef2f7; border: none; border-radius: 999px;
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
      border-color: rgba(30,95,214,.35); background: var(--accent-soft);
    }
    .as-card-check {
      width: 24px; height: 24px; border-radius: 50%; border: 1.5px solid #d4dae2;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      font-size: 13px; color: transparent; margin-top: 1px; transition: all .15s;
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
      background: #f1f4f8; border: 1px solid var(--border); border-radius: 10px;
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


# Redaktionelle Byline (zentral, damit alte Seiten beim Build normalisiert werden).
_BYLINE = 'Von der „Presse“-Redaktion'


def _ressort_tag_str(name: str) -> str:
    name = name.strip()
    hue = _RESSORT_HUE.get(name.split("/")[0].split()[0].lower(), 24)
    return f'<span class="ressort" style="--h:{hue}">{name}</span>'


def _meta_tag(m: re.Match) -> str:
    """„(Ressort · Bericht: Name)" → Ressort-Pill + Quellenzeile."""
    ressort, _, bericht = m.group(1).partition("·")
    out = _ressort_tag_str(ressort)
    if "Bericht:" in bericht:
        name = bericht.split("Bericht:", 1)[1].strip()
        if name:
            out += f' <span class="byline-source">Bericht: {name}</span>'
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


def _pick_greeting(edition: str, datum_iso: str) -> str:
    # Demo-Personalisierung: feste Begrüßung für die Vorführ-Ausgabe (15. Juni, morgen).
    if datum_iso == "2026-06-15" and edition == "morgen":
        return "Guten Morgen, Andreas Rast."
    pool = _GREETING_POOL.get(edition, ["Dein Lagebild."])
    try:
        idx = date.fromisoformat(datum_iso).toordinal() % len(pool)
    except (ValueError, TypeError):
        idx = 0
    return pool[idx]


def _next_edition_hint(edition: str) -> str:
    """Dezente Rhythmus-Zeile für die Startseite (nächstes Lagebild + Presse-Takt)."""
    if edition not in _EDITION_ORDER:
        return ""
    i = _EDITION_ORDER.index(edition)
    nxt = _EDITION_ORDER[(i + 1) % len(_EDITION_ORDER)]
    when = "morgen" if i == len(_EDITION_ORDER) - 1 else "heute"
    return (
        '<p class="next-edition">'
        f"Nächstes Lagebild: {when} {_EDITION_TIME[nxt]} Uhr · "
        "Die Presse kuratiert um 6, 11, 16 &amp; 20 Uhr"
        "</p>"
    )


def _lagebild_header(datum_iso: str, edition: str, points: int, lesezeit: int | None) -> str:
    """Baut den Seitenkopf: Kicker (Datum · Ausgabe), Begrüßung, Meta-Byline."""
    try:
        d = date.fromisoformat(datum_iso)
        kicker = f"{WEEKDAYS[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]} · {_EDITION_LABEL.get(edition, edition)}"
    except (ValueError, TypeError):
        kicker = _EDITION_LABEL.get(edition, edition)
    greeting = _pick_greeting(edition, datum_iso)
    meta = [_BYLINE]
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
            f'<button class="fb-btn" data-vote="up">Relevant</button>'
            f'<button class="fb-btn" data-vote="down">Weniger</button>'
            f"</div>"
        )
        return m.group(0).rstrip() + bar

    # Jeder Artikel reicht von <h2>[Ziffer] bis zum nächsten <h2>[Ziffer] oder <hr>
    return re.sub(r"<h2>[1-9].*?(?=<h2>[1-9]|<hr>)", _insert, content, flags=re.DOTALL)


def _enhance_content(content: str, datum: str = "", edition: str = "") -> str:
    """Verleiht dem Roh-Inhalt Die-Presse-Charakter (Pills, Kicker, Highlight-Box)."""
    # Etwaigen Audio-Player aus früherem Build entfernen (wird in build_site neu,
    # mit korrektem Pfad, eingesetzt) — hält das erneute Rendern idempotent.
    content = re.sub(
        r'<div class="audio-player">.*?</div>\s*', "", content, flags=re.DOTALL
    )
    # Marken-Zeile entfernen (steht jetzt im Masthead) — als <p> oder <div>.
    content = re.sub(
        r'<(p|div)[^>]*class="brand"[^>]*>.*?</\1>\s*', "", content, flags=re.DOTALL
    )
    # Meta-Klammer „(Ressort · Bericht: Name)" direkt vor dem „→ Artikel"-Link:
    # Ressort als farbiges Pill, Autor als Quellenzeile (vor dem Link-Umbau).
    if 'class="ressort"' not in content:
        content = re.sub(
            r'\(([^)]{2,60})\)\s*(?=<a[^>]*>→ Artikel</a>)', _meta_tag, content
        )
    # Quell-Links als rote Primary-Pill auszeichnen.
    content = re.sub(
        r'<a href="([^"]+)">→ Artikel</a>',
        r'<a class="source-link" href="\1">Weiterlesen bei der Presse →</a>',
        content,
    )
    # Seitenkopf neu bauen: H1 (+ etwaige alte Byline) durch Kicker/Begrüßung/Meta ersetzen.
    if datum:
        points = len(re.findall(r"<h2>\s*[1-9]", content))
        m = re.search(r"Lesezeit ca\.\s*(\d+)\s*Sekunden", content)
        lesezeit = int(m.group(1)) if m else None
        header = _lagebild_header(datum, edition, points, lesezeit)
        if '<header class="lagebild-header">' in content:
            # Idempotent: bestehenden Header komplett ersetzen (kein Verschachteln).
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
        # Fallback (kein Datum): nur Byline normalisieren bzw. einsetzen.
        content = re.sub(
            r'<p class="byline">.*?</p>',
            f'<p class="byline">{_BYLINE}</p>', content, count=1, flags=re.DOTALL,
        )
        if 'class="byline"' not in content:
            content = re.sub(
                r"(</h1>)", rf'\1\n<p class="byline">{_BYLINE}</p>', content, count=1
            )
    # Redakteur:innen-Fußzeile als eigene Klasse auszeichnen.
    content = re.sub(
        r'<p><em>(Heute mit Berichterstattung von:.*?)</em></p>',
        r'<p class="reporters">\1</p>', content, count=1, flags=re.DOTALL,
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

    content = "<h1>Meine Themen</h1>\n" + assessment_html + _PUSH_SECTION
    html = _render_page("Meine Themen", content, "dossier")
    (SITE_DIR / "dossier.html").write_text(html, encoding="utf-8")


# Push-Aktivierung — eigenständiger Block am Ende des Themen-Screens. Versteckt sich
# selbst, wenn der Browser kein Push kann oder kein VAPID_PUBLIC_KEY gesetzt ist.
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
    return;  // Push nicht unterstützt oder kein Schlüssel — Block bleibt verborgen.
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

# Service Worker: Seiten network-first (frisches Lagebild zuerst, Cache als
# Offline-Fallback), statische/Fremd-Assets cache-first. Cache-Version im Namen,
# damit ein Deploy alte Caches verdrängt.
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

// Web-Push: Notification anzeigen und bei Klick die PWA öffnen.
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


def _write_pwa_assets() -> None:
    """Schreibt Web-App-Manifest, Service Worker und Push-Config (Public-Key)."""
    import os
    SITE_DIR.mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "manifest.webmanifest").write_text(
        json.dumps(_MANIFEST, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (SITE_DIR / "sw.js").write_text(_SERVICE_WORKER, encoding="utf-8")
    # VAPID-Public-Key (öffentlich) für den Client. Leer ⇒ Push-UI bleibt verborgen.
    vapid_public = os.environ.get("VAPID_PUBLIC_KEY", "")
    (SITE_DIR / "push-config.js").write_text(
        f'window.VAPID_PUBLIC_KEY = "{vapid_public}";\n', encoding="utf-8"
    )


def _audio_player(src: str) -> str:
    """HTML-Block für den Lagebild-Audioplayer, oder '' wenn keine mp3 da ist."""
    return (
        '<div class="audio-player">'
        '<span class="audio-label">▶ Lagebild zum Hören</span>'
        f'<audio controls preload="none" src="{src}"></audio>'
        "</div>\n"
    )


def _insert_after_header(content: str, snippet: str) -> str:
    """Fügt `snippet` direkt nach dem Seitenkopf ein (Fallback: nach </h1>, sonst voran)."""
    if "</header>" in content:
        return content.replace("</header>", "</header>\n" + snippet, 1)
    if "</h1>" in content:
        return content.replace("</h1>", "</h1>\n" + snippet, 1)
    return snippet + content


def _prune_old_audio(days: int = 14) -> None:
    """Löscht mp3-Dateien im Archiv, die älter als `days` Tage sind."""
    from datetime import timedelta

    cutoff = date.today() - timedelta(days=days)
    for mp3 in ARCHIV_DIR.glob("*.mp3"):
        m = re.match(rf"^(\d{{4}})-(\d{{2}})-(\d{{2}})-({_EDITIONS_RE})\.mp3$", mp3.name)
        if not m:
            continue
        try:
            d = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        if d < cutoff:
            mp3.unlink()


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
        # Audio-Ausgaben mitkopieren (Lagebild zum Hören).
        for mp3 in OUT_DIR.glob("*.mp3"):
            if re.match(rf"^\d{{4}}-\d{{2}}-\d{{2}}-({_EDITIONS_RE})\.mp3$", mp3.name):
                shutil.copy2(mp3, ARCHIV_DIR / mp3.name)
    _prune_old_audio()

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
        mp3_name = f"{d.isoformat()}-{edition}.mp3"
        if (ARCHIV_DIR / mp3_name).exists():
            content = _insert_after_header(content, _audio_player(mp3_name))
        branded = _render_page(_label(d, edition), content, "archiv", root="../")
        path.write_text(branded, encoding="utf-8")

    build_archiv_index(editions)

    # Hauptseite: neueste Ausgabe — mit Streak-Ritus ganz oben.
    latest_html = editions[0][1].read_text(encoding="utf-8")
    latest_d, _, latest_edition = editions[0][0]
    latest_content = _extract_body(latest_html, latest_d.isoformat(), latest_edition)
    # Reihenfolge nach dem Header: Streak-Chip, dann Audio-Player.
    from . import state as state_mod
    latest_mp3 = f"{latest_d.isoformat()}-{latest_edition}.mp3"
    if (ARCHIV_DIR / latest_mp3).exists():
        latest_content = _insert_after_header(
            latest_content, _audio_player(f"archiv/{latest_mp3}")
        )
    streak = state_mod.current_streak(state)
    if streak >= 2:
        latest_content = _insert_after_header(
            latest_content,
            f'<div class="streak">🔥 {streak} Tage in Folge informiert</div>\n',
        )
    # Dezente Rhythmus-Zeile direkt unter dem Header (nur Startseite).
    hint = _next_edition_hint(latest_edition)
    if hint:
        latest_content = _insert_after_header(latest_content, hint)
    title = _label(latest_d, latest_edition)
    index_html = _render_page(title, latest_content, "lagebild")
    index.write_text(index_html, encoding="utf-8")

    print(f"Web-App gebaut: {index} ({len(editions)} Ausgabe(n) im Archiv)")
    return index
