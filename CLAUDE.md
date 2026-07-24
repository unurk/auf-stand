# Copilot — Die Presse als Hintergrund-Dienst (MVP)

## Was dieses Projekt ist

Prototyp für ein neues Digitalprodukt der „Presse": Statt eines Artikel-Feeds bekommt
die Nutzerin **4× täglich** ein **Lagebild** — eine redaktionelle Synthese von 3–5
Entwicklungen je nach Nachrichtenlage (an ruhigen Tagen weniger), die sich materiell
geändert haben. Die vier Ausgaben sind an den **Presse-Kuratierungstakt** (Rebrush 2026)
angedockt: **06:00 · 11:00 · 16:00 · 20:00 Uhr**. Lesezeit rund 90 Sekunden (an dichten
Tagen etwas mehr), am Ende das Signal „Du bist informiert ✓". Vorbild ist die Produktlogik
von WHOOP: arbeitet im Hintergrund, verdichtet, meldet sich nur zu relevanten Momenten.

Wichtigste Produktregel: **Wir optimieren auf Time-to-Informed (kurz!), nicht auf
Time-on-Site.** Jedes Feature, das Scrollen, Stöbern oder längere Sessions fördert,
widerspricht dem Produkt und wird nicht gebaut.

## Architektur

```
copilot/
  fetch.py       RSS-Feeds holen & normalisieren (nur öffentliche Teaser; httpx + Timeout)
  state.py       Laufzeit-Zustand: gesehene Artikel, Feedback, Dossier, Push-Abos, Stats,
                 Lese-Signale, Wirkungs-Profil, „hat gefehlt"-Meldungen
  qualitaet.py   Qualitäts-Gate nach der Synthese: leere Themen-Deltas raus,
                 Tracker-Abschnitt gedeckelt, Lesezeit-Budget gemessen
  profil.py      Wirkungs-Profil (Betroffenheit statt Interesse) → „Für dich konkret"
  karte.py       Teilbare Bild-Karte zum wichtigsten Punkt (matplotlib)
  podcast.py     RSS-Feed der Audio-Ausgaben (Apple Podcasts, Spotify, CarPlay)
  synthesize.py  Prompt bauen + Synthese über Provider (anthropic | glm via OpenRouter)
  render.py      Markdown- und HTML-Ausgabe nach out/
  deliver.py     Optionaler E-Mail-Versand (SMTP via .env), sonst nur Datei
  telegram.py    Telegram-Versand (MarkdownV2, Feedback-Buttons, Audio, Alerts)
  tts.py         Audio-Version des Lagebilds (OpenAI TTS, best-effort)
  webpush.py     Web-Push an PWA-Abonnenten (VAPID)
  webview.py     Statische PWA (site/): Lagebild, Dossier, Archiv — Presse + NYT
  rueckkanal.py  Telegram-Rückkanal: Fragen, /themen, /thema-neu, /push, Feedback-Taps
  quittung.py    Wochen-Quittung als Bild-Karte (Samstag)
  epaper.py      E-Paper-Verweis am Ende jeder Ausgabe
  vorausschau.py Termin-Vorausschau in der Morgen-Ausgabe
  i18n.py        Deutsche/englische Textbausteine (Presse- vs. NYT-Edition)
  main.py        CLI: morgen|mittag|nachmittag|abend|catchup|feeds|woche|rueckkanal|site|karte [--dry-run]
prompts/
  lagebild.md    Der redaktionelle Kern-Prompt (das Herz des Produkts; .en.md für NYT)
manual_input/    Hier können Volltexte (Premium) als .txt/.md abgelegt werden
config.yaml      Feeds, Themen-Tracker, Empfänger, Provider/Modell (config.nyt.yaml: NYT)
data/state.json  Laufzeit-Zustand (gesehene Artikel; state.nyt.json für die NYT-Edition)
out/             Erzeugte Lagebilder (md + html + mp3)
tests/           pytest-Suite (hermetisch, ohne Netz) — läuft in CI bei jedem Push
```

Ablauf einer Ausgabe: fetch -> state filtert auf „neu seit letzter Ausgabe" ->
synthesize (Claude oder GLM, je nach `provider` in config.yaml) -> qualitaet
(Gate) -> render -> deliver/telegram/tts/karte/webpush -> state aktualisieren.
Ist nichts Neues da, geht statt Schweigen eine kurze Ruhe-Ausgabe raus.

## Konventionen

- Python 3.10+, keine Frameworks. Abhängigkeiten minimal halten (requirements.txt).
- Alle Nutzertexte und Prompts auf Deutsch (österreichisches Publikum).
- Secrets nur über .env (siehe .env.example), niemals in Code oder config.yaml.
- `--dry-run` muss immer funktionieren: baut den Prompt und schreibt ihn nach out/,
  ohne API-Call. So ist die Pipeline ohne Kosten testbar.
- Das Qualitäts-Gate im Prompt nicht aufweichen: Lieber 1 Punkt oder die ehrliche
  Aussage „heute wenig Wesentliches" als 3 erzwungene Punkte.

## Content-Zugang (wichtig)

- RSS-Feeds (diepresse.com/rss/<Ressort>) sind öffentlich: Headlines + Teaser.
  Feed-URLs regelmäßig verifizieren (`python -m copilot.main feeds` — Exit-Code 1,
  sobald auch nur ein Feed leer bleibt). Das Ressort-Schema ändert sich: Zuletzt
  waren Aussenpolitik, EU und Tech auf 404 gelaufen und Unternehmen antwortete mit
  200, aber ohne Einträge — vier von neun Feeds still tot. Ein Feed ohne Artikel
  gilt darum als Fehler, nicht als „heute nichts Neues".
- Volltexte: Der User hat ein Premium-Abo und arbeitet bei der Presse. Für den
  Prototyp werden Volltexte manuell in `manual_input/` abgelegt (Datei pro Artikel).
  KEIN Login-Scraping mit persönlichen Zugangsdaten bauen — für den echten Pilot
  soll ein offizieller interner Content-Feed/API über die IT angefragt werden.
  Das ist auch der bessere Weg für saubere, vollständige Daten.

## Stand & Roadmap

Gebaut und in Betrieb: 4 Ausgaben/Tag via GitHub Actions, Telegram (inkl.
👍/👎-Feedback, Rückkanal, Audio), E-Mail, PWA mit Web-Push, Themen-Dossiers,
Wochen-Quittung, NYT-Parallel-Edition, pytest-Suite in CI.

Dazugekommen (Konsumenten-Ausbau):

- **Qualitäts-Gate** (`qualitaet.py`): hält Themen-Abschnitt und Lesezeit im Budget
- **Wirkungs-Profil** (`profil.py`): „Für dich konkret"-Zeile statt behaupteter Relevanz
- **Lese-Signale statt Zustell-Zählung**: Streak, Quittung und Nachhol-Leiste
  messen die Leserin, nicht unseren Cron
- **Vollständigkeits-Beweis**: „geprüft, nicht aufgenommen" + `/fehlt`-Rückmeldung
- **Reifegrad** je Punkt (Gerücht → Entwurf → Beschlossen → Gilt ab) und **Nachtrag**
- **Ruhe-Ausgabe**, **Podcast-Feed** (`podcast.py`), **Teilen-Karte** (`karte.py`),
  **Wochen-Quiz**

Als Nächstes sinnvoll:

1. Prompt-Qualität weiter iterieren (Feedback-Daten aus data/state.json nutzen)
2. E-Mail-Versand an kleine Testgruppe (Concierge-MVP, siehe Konzeptpapier)
3. Offiziellen Content-Feed/API über die Presse-IT anfragen (Volltexte statt Teaser)
4. webview.py entflechten (2000+ Zeilen: Templates auslagern, Presse/NYT trennen)
5. Mehrbenutzer-Fähigkeit: State ist einbenutzerlich (ein Profil, ein Lese-Stand) —
   vor der Testgruppe (Punkt 2) muss er pro Empfänger:in getrennt werden

## Was bewusst NICHT gebaut wird

- Kein Artikel-Feed, keine Endlos-Liste, kein „Mehr laden"
- Keine Klick-Personalisierung; Themen-Tracker sind explizit gewählte Themen
- Kein Dauerrauschen: Ausgaben/Pushes ausschließlich zu den vier festen
  Presse-Kuratierungszeiten (06/11/16/20). Die festen Zeitpunkte sind selbst der
  Anti-Doomscroll-Mechanismus — keine beliebigen Zusatz-Pushes dazwischen.
  (Frühere Regel „max. 2/Tag" bewusst auf den Presse-Rebrush-Takt umgestellt.)
- Credential-basiertes Scraping hinter der Paywall

## Auslösung / Timing

Die Ausgaben laufen in GitHub Actions (`.github/workflows/lagebild.yml`). Verlässlich
**pünktlich** ist nur der externe Trigger: cron-job.org stößt 4×/Tag + Sa den Workflow per
`workflow_dispatch`-API an (Setup: `scripts/setup_cron.sh`, Doku im README). Jeder Trigger
benennt die Ausgabe explizit über den `edition`-Workflow-Input. Die GitHub-eigenen
`schedule`-Crons sind erwiesenermaßen unzuverlässig (verspätet/ausgelassen) und bleiben nur
als Best-Effort-Fallback; der Block-Guard in `main.py` hält Doppelläufe idempotent.
