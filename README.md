# Copilot — MVP

Prototyp für das Konzept „Die Presse als Hintergrund-Dienst": **4× täglich**
(06:00 · 11:00 · 16:00 · 20:00, der Presse-Kuratierungstakt) ein **Lagebild**
(3–5 materielle Entwicklungen je nach Nachrichtenlage, rund 90 Sekunden Lesezeit)
statt eines Artikel-Feeds. Zustellung per Telegram (mit 👍/👎-Feedback und
Audio-Version), E-Mail und als PWA mit Web-Push; dazu Themen-Dossiers und eine
Wochen-Quittung. Hintergrund siehe `CLAUDE.md` und das Konzeptpapier.

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
python -m copilot.main feeds

# 2. Pipeline ohne API-Kosten testen — baut den Prompt und legt ihn in out/ ab:
python -m copilot.main morgen --dry-run

# 3. Erstes echtes Lagebild erzeugen (braucht ANTHROPIC_API_KEY in .env):
python -m copilot.main morgen
# -> out/JJJJ-MM-TT-morgen.md und .html (im Browser öffnen)

# 17-Uhr-Update (zeigt nur, was seit der Morgen-Ausgabe neu ist):
python -m copilot.main abend

# Nach Urlaub/Pause:
python -m copilot.main catchup

# Teilbare Bild-Karte zum wichtigsten Punkt der jüngsten Ausgabe:
python -m copilot.main karte
```

`--keep-seen` verhindert beim Testen, dass Artikel als „gesehen" markiert werden.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Läuft auch in CI (`.github/workflows/test.yml`) bei jedem Push auf Code/Config.

## Synthese-Provider (Claude oder GLM)

Standard ist die Anthropic-API (`provider: anthropic`, Modell in `config.yaml`).
Zum A/B-Testen kann in `config.yaml` `provider: glm` gesetzt werden — dann läuft
die Synthese über GLM via OpenRouter (OpenAI-kompatibel, braucht `ZAI_API_KEY`
in `.env` bzw. als GitHub-Secret).

## Volltexte nutzen (Premium-Abo)

RSS liefert nur Teaser. Für tiefere Synthese: Volltexte als .txt/.md in
`manual_input/` ablegen (erste Zeile = Titel) — sie haben bei der Synthese Vorrang.
Für den echten Pilot: offiziellen Content-Feed über die Presse-IT anfragen,
kein Login-Scraping bauen.

## Telegram-Rückkanal

Der Bot beantwortet freie Fragen auf Basis der aktuellen Artikel und versteht:

- `/themen EZB Miet Börse` — Themen-Präferenzen setzen (Schlagworte aus config.yaml)
- `/thema-neu Name|Schlagwort` — eigenes Thema als Tracker hinzufügen
- `/push <Code aus der PWA>` — Web-Push-Benachrichtigungen aktivieren
- `/profil` — Wirkungs-Profil per Knopfdruck ausfüllen (`/profil <Code aus der PWA>`
  übernimmt es aus der App, `/profil loeschen` verwirft es)
- `/fehlt <Thema>` — melden, was im Lagebild gefehlt hat
- `/gelesen` — Lese-Signal setzen (z. B. nach der Audio-Version)

Unter jeder Ausgabe stehen zusätzlich die Knöpfe **✓ Gelesen** und
**🔍 Hat was gefehlt?**.

## Wirkungs-Profil (Betroffenheit statt Interesse)

Themen-Tracker sagen, was interessiert. Das Wirkungs-Profil (zehn Fragen:
Miete/Eigentum, Kredit variabel/fix, Heizung, Mobilität, Ersparnisse …) sagt, wie
eine Entscheidung *trifft*. Die Synthese hängt damit an passende Punkte eine Zeile
**„Für dich konkret: …"**. Es steuert ausschließlich die Einordnung, nie die
Auswahl der Entwicklungen — und wird selbst deklariert, nicht aus Klicks
erschlossen. Ausfüllen im Themen-Screen der PWA oder per `/profil` im Chat.

## Was die Ausgabe im Zeitbudget hält

`copilot/qualitaet.py` zieht nach der Synthese die Produktregeln nach: Themen-Deltas
ohne materielle Änderung fliegen raus, der Abschnitt „Deine Themen" wird auf drei
Zeilen gedeckelt. Reißt die Lesezeit im Schnitt der letzten Ausgaben das Budget
(`lesezeit_budget_sekunden`, Standard 90), geht ein Kürzungs-Hinweis als
Kalibrierung in den nächsten Prompt.

## Podcast-Feed

Jeder Site-Build erzeugt `site/feed.xml` aus den Audio-Ausgaben im Archiv — die
Adresse in Apple Podcasts, Overcast oder Pocket Casts eingefügt, läuft das Lagebild
im Auto und auf dem Lautsprecher. Die Feed-Adresse steht im Themen-Screen der PWA.

## Ruhige Blöcke

Erreicht in einem Block nichts die Schwelle, wird das **zugestellt** statt
verschwiegen: eine Zeile „Ruhige Lage — keine der N geprüften Meldungen hat die
Schwelle erreicht". Ohne diese Meldung ist ein ruhiger Nachrichtentag von einem
kaputten Dienst nicht unterscheidbar.

Der Rückkanal läuft nach jeder Ausgabe in der Pipeline (`python -m copilot.main rueckkanal`).

## Englische NYT-Edition (`config.nyt.yaml`)

Dieselbe Pipeline kann ein **englisches Briefing aus öffentlichen New-York-Times-
RSS-Feeds** erzeugen (im Stil von „Today's Paper"). Alles läuft über eine zweite
Config — das deutsche Presse-Produkt bleibt unberührt:

```bash
# Feeds prüfen:
python -m copilot.main feeds  --config config.nyt.yaml
# Prompt bauen ohne API-Kosten:
python -m copilot.main morgen --config config.nyt.yaml --dry-run
# Echtes Briefing (braucht ANTHROPIC_API_KEY):
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
