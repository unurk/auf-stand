# Copilot — MVP

Prototyp für das Konzept „Die Presse als Hintergrund-Dienst": 1–2x täglich ein
**Lagebild** (3–5 materielle Entwicklungen je nach Nachrichtenlage, rund 90 Sekunden
Lesezeit) statt eines Artikel-Feeds. Hintergrund siehe `CLAUDE.md` und das Konzeptpapier.

## Setup (einmalig, ~5 Minuten)

```bash
cd auf-stand
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env    # OPENROUTER_API_KEY eintragen (openrouter.ai/keys)
```

## Erste Schritte

```bash
# 1. Feeds verifizieren (URLs können sich ändern):
python -m copilot.main feeds

# 2. Pipeline ohne API-Kosten testen — baut den Prompt und legt ihn in out/ ab:
python -m copilot.main morgen --dry-run

# 3. Erstes echtes Lagebild erzeugen (braucht OPENROUTER_API_KEY in .env):
python -m copilot.main morgen
# -> out/JJJJ-MM-TT-morgen.md und .html (im Browser öffnen)

# 17-Uhr-Update (zeigt nur, was seit der Morgen-Ausgabe neu ist):
python -m copilot.main abend

# Nach Urlaub/Pause:
python -m copilot.main catchup
```

`--keep-seen` verhindert beim Testen, dass Artikel als „gesehen" markiert werden.

## Volltexte nutzen (Premium-Abo)

RSS liefert nur Teaser. Für tiefere Synthese: Volltexte als .txt/.md in
`manual_input/` ablegen (erste Zeile = Titel) — sie haben bei der Synthese Vorrang.
Für den echten Pilot: offiziellen Content-Feed über die Presse-IT anfragen,
kein Login-Scraping bauen.

## Englische NYT-Edition (`config.nyt.yaml`)

Dieselbe Pipeline kann ein **englisches Briefing aus öffentlichen New-York-Times-
RSS-Feeds** erzeugen (im Stil von „Today's Paper"). Alles läuft über eine zweite
Config — das deutsche Presse-Produkt bleibt unberührt:

```bash
# Feeds prüfen:
python -m copilot.main feeds  --config config.nyt.yaml
# Prompt bauen ohne API-Kosten:
python -m copilot.main morgen --config config.nyt.yaml --dry-run
# Echtes Briefing (braucht OPENROUTER_API_KEY):
python -m copilot.main morgen --config config.nyt.yaml
```

Die NYT-Config wählt Sprache und Prompt (`language: en`, `prompt_file: lagebild.en.md`),
führt einen **eigenen State** (`state_file: data/state.nyt.json`, getrennt von der
Presse-Ausgabe) und verlinkt am Ende „Today's Paper". Quelle sind ausschließlich die
öffentlichen RSS-Feeds (Headlines + Teaser) — **kein** Login-Scraping hinter der Paywall
(siehe `CLAUDE.md`). Volltexte bei Bedarf wie gehabt über `manual_input/`.

## Zuverlässiges Timing (cron-job.org → GitHub Actions)

Die vier Ausgaben (06/11/16/20 Uhr Wien) + die Wochen-Quittung laufen in GitHub
Actions. GitHubs **interner** Schedule-Cron ist aber unzuverlässig (feuert
verspätet, lässt Läufe aus). Verlässlich pünktlich wird es durch einen **externen
Trigger**, der den Workflow per `workflow_dispatch`-API anstößt (startet <1 min):

```
CRONJOB_KEY=<cron-job.org-API-Key> GH_TOKEN=<GitHub-PAT> bash scripts/setup_cron.sh
```

Einmalig nötig:

1. **GitHub Fine-grained PAT** auf `unurk/auf-stand`, Permission **Actions: Read and
   write** → als `GH_TOKEN`.
2. **cron-job.org**-Konto (kostenlos) → API-Key → als `CRONJOB_KEY`.
3. Script ausführen — es legt fünf Jobs in der Zeitzone *Europe/Vienna* an (ganzjährig
   pünktlich, kein DST-Drift) und benennt je Job die Ausgabe explizit über den
   `edition`-Input des Workflows. Erneutes Ausführen ist idempotent.
4. Verifizieren: auf cron-job.org bei einem Job *„Run now"* → in GitHub Actions
   erscheint <1 min ein `workflow_dispatch`-Lauf, Telegram-/Web-Push kommt sofort.

Secrets (PAT, API-Key) **niemals** ins Repo committen — nur zur Laufzeit übergeben;
der PAT lebt allein in den cron-job.org-Job-Headern. Die GitHub-Schedule-Crons im
Workflow bleiben als Best-Effort-Fallback erhalten.

**Lokal/manuell** geht weiter über die CLI, z. B. `crontab -e`:

```
0 6  * * * cd /pfad/zu/auf-stand && .venv/bin/python -m copilot.main morgen
0 17 * * * cd /pfad/zu/auf-stand && .venv/bin/python -m copilot.main abend
```

E-Mail-Versand: SMTP-Daten in `.env`, Empfänger in `config.yaml` unter `recipients`.

## Mit Claude Code weiterbauen

Im Projektordner `claude` starten — `CLAUDE.md` gibt Kontext, Konventionen und
die Roadmap vor. Sinnvolle erste Aufträge:

1. „Führe `python -m copilot.main feeds` aus und repariere ggf. die Feed-URLs
   in config.yaml."
2. „Erzeuge ein Lagebild mit --dry-run, lies den Prompt in out/ und schlage
   Verbesserungen am Auswahlprinzip in prompts/lagebild.md vor."
3. „Baue die 17-Uhr-Ausgabe als Audio: TTS-Anbindung, mp3 nach out/."
4. „Baue einen Telegram-Bot als Zustellkanal (Bot-Token über .env)."
