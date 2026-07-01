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
  fetch.py       RSS-Feeds der Presse holen & normalisieren (nur öffentliche Teaser)
  state.py       Gesehene Artikel in data/state.json -> Delta zwischen Ausgaben
  synthesize.py  GLM-5.2 via OpenRouter: erzeugt das Lagebild aus Artikeln + Themen-Trackern
  render.py      Markdown- und HTML-Ausgabe nach out/
  deliver.py     Optionaler E-Mail-Versand (SMTP via .env), sonst nur Datei
  main.py        CLI: morgen | mittag | nachmittag | abend | catchup [--dry-run]
prompts/
  lagebild.md    Der redaktionelle Kern-Prompt (das Herz des Produkts)
manual_input/    Hier können Volltexte (Premium) als .txt/.md abgelegt werden
config.yaml      Feeds, Themen-Tracker, Empfänger, Modell
data/state.json  Laufzeit-Zustand (gesehene Artikel)
out/             Erzeugte Lagebilder (md + html)
```

Ablauf einer Ausgabe: fetch -> state filtert auf „neu seit letzter Ausgabe" ->
synthesize (GLM-5.2 via OpenRouter) -> render -> deliver -> state aktualisieren.

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
  Feed-URLs beim ersten Lauf verifizieren (`python -m copilot.main feeds`).
- Volltexte: Der User hat ein Premium-Abo und arbeitet bei der Presse. Für den
  Prototyp werden Volltexte manuell in `manual_input/` abgelegt (Datei pro Artikel).
  KEIN Login-Scraping mit persönlichen Zugangsdaten bauen — für den echten Pilot
  soll ein offizieller interner Content-Feed/API über die IT angefragt werden.
  Das ist auch der bessere Weg für saubere, vollständige Daten.

## Roadmap (in dieser Reihenfolge sinnvoll)

1. Feeds verifizieren, erste echte Lagebilder erzeugen, Prompt-Qualität iterieren
2. Themen-Tracker schärfen: Delta-Formulierung („Was ist neu seit deinem letzten Stand")
3. E-Mail-Versand an kleine Testgruppe (Concierge-MVP, siehe Konzeptpapier)
4. 17-Uhr-Ausgabe als Audio: TTS-Anbindung (z. B. ElevenLabs/OpenAI TTS), mp3 nach out/
5. Telegram-Bot als Push-Kanal (einfacher als WhatsApp Business API)
6. Mini-Web-Ansicht mit „Du bist informiert ✓"-Status (statisches HTML reicht zunächst)

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
