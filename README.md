# Auf Stand — MVP

Prototyp für das Konzept „Die Presse als Hintergrund-Dienst": 1–2x täglich ein
**Lagebild** (max. 3 materielle Entwicklungen, ≤ 90 Sekunden Lesezeit) statt
eines Artikel-Feeds. Hintergrund siehe `CLAUDE.md` und das Konzeptpapier.

## Setup (einmalig, ~5 Minuten)

```bash
cd auf-stand
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # ANTHROPIC_API_KEY eintragen (console.anthropic.com)
```

## Erste Schritte

```bash
# 1. Feeds verifizieren (URLs können sich ändern):
python -m auf_stand.main feeds

# 2. Pipeline ohne API-Kosten testen — baut den Prompt und legt ihn in out/ ab:
python -m auf_stand.main morgen --dry-run

# 3. Erstes echtes Lagebild erzeugen (braucht ANTHROPIC_API_KEY in .env):
python -m auf_stand.main morgen
# -> out/JJJJ-MM-TT-morgen.md und .html (im Browser öffnen)

# 17-Uhr-Update (zeigt nur, was seit der Morgen-Ausgabe neu ist):
python -m auf_stand.main abend

# Nach Urlaub/Pause:
python -m auf_stand.main catchup
```

`--keep-seen` verhindert beim Testen, dass Artikel als „gesehen" markiert werden.

## Volltexte nutzen (Premium-Abo)

RSS liefert nur Teaser. Für tiefere Synthese: Volltexte als .txt/.md in
`manual_input/` ablegen (erste Zeile = Titel) — sie haben bei der Synthese Vorrang.
Für den echten Pilot: offiziellen Content-Feed über die Presse-IT anfragen,
kein Login-Scraping bauen.

## Automatisieren (täglich 6:00 und 17:00)

macOS/Linux, `crontab -e`:

```
0 6  * * * cd /pfad/zu/auf-stand && .venv/bin/python -m auf_stand.main morgen
0 17 * * * cd /pfad/zu/auf-stand && .venv/bin/python -m auf_stand.main abend
```

E-Mail-Versand: SMTP-Daten in `.env`, Empfänger in `config.yaml` unter `recipients`.

## Mit Claude Code weiterbauen

Im Projektordner `claude` starten — `CLAUDE.md` gibt Kontext, Konventionen und
die Roadmap vor. Sinnvolle erste Aufträge:

1. „Führe `python -m auf_stand.main feeds` aus und repariere ggf. die Feed-URLs
   in config.yaml."
2. „Erzeuge ein Lagebild mit --dry-run, lies den Prompt in out/ und schlage
   Verbesserungen am Auswahlprinzip in prompts/lagebild.md vor."
3. „Baue die 17-Uhr-Ausgabe als Audio: TTS-Anbindung, mp3 nach out/."
4. „Baue einen Telegram-Bot als Zustellkanal (Bot-Token über .env)."
