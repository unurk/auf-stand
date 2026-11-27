# Übergabe: Betrieb ohne Bot (ab 1.12.2026)

Bis 30.11.2026 hat ein externer Bot jeden Morgen die 06-Uhr-Ausgabe geprüft,
Aufträge an Claude Code formuliert und die PRs gemergt. Ab 1.12. läuft das so:

| Was | Wer | Kosten / Secret |
|---|---|---|
| Ausgaben erzeugen (4×/Tag) | GitHub Actions `lagebild.yml` — wie bisher | unverändert |
| **Täglich prüfen** (06:40 Wien) | GitHub Actions `qualitaet.yml` → `copilot/pruefung.py` | keine; nur vorhandene Secrets |
| Bei Befund melden | GitHub-Issue (Label `qualitaetscheck`) + Telegram-Alarm | keine |
| **Befund beheben** | Claude Code — täglich 07:00 als geplante Session (oder von Hand per Einzeiler) | Claude-Abo, kein neues Secret |
| Mergen | Claude per Auto-Merge nach der Regel unten, sonst Unur | — |

## Was der tägliche Check prüft

Gelesen wird genau das, was die Leserin sieht: `site/archiv/<datum>-morgen.html`.

- Ausgabe da und pünktlich (spätestens 90 Min. nach 06:00; nicht Stunden zu früh)
- Schlagzeile/Punkt-Titel gegen Text: Zahlen, Absicht ≠ Vollzug, keine fremden Aussagen
- Wochentag gegen Datum („ab Montag" bei „1. Dezember")
- „Heute wichtig" = Punkte, jeder Punkt mit „Weiterlesen bei der Presse"
- Lesezeit ≤ 90 s

Kein Befund → kein Issue, keine Nachricht. Für eine andere Ausgabe oder einen
anderen Tag: Actions → „Qualitätscheck" → *Run workflow*.

## Einzeiler für eine neue Claude-Code-Session

> Lies UEBERGABE.md und arbeite die offenen GitHub-Issues mit Label qualitaetscheck ab – je Issue Ursache belegen, fixen, Test, PR gegen master; danach Issue mit PR-Link kommentieren.

## Regeln für jede Session

1. **Unur ist der einzige Leser.** Keine Features für eine Zielgruppe, keine Mehrbenutzer-Umbauten.
2. **Nur stabilisieren.** Fehler beheben, die der Check oder Unur meldet. Keine neuen Features,
   kein Umbau ohne Befund. Im Zweifel kleiner.
3. **Ursache belegen**, nicht raten: Lauf-Log (`gh api repos/unurk/auf-stand/actions/runs/<id>/logs`),
   Archiv-Seite, Code-Stelle. Im PR nennen, was belegt ist und was Vermutung bleibt.
4. **Deterministisch vor LLM.** Fixes als Prüfregel nach der Synthese (`qualitaet.py`,
   `titelcheck.py`, `zeittreue.py`, `budget.py`); Prompt-Änderungen nur zusätzlich.
5. **Regressionstest mit genau dem Fall** + Archiv-Gegenprobe (wie oft hätte die Regel gegriffen,
   wie viele Fehlalarme).
6. **Keine Secrets in Code oder config.yaml**, keine neuen Secrets, keine kostenpflichtigen Dienste.
7. **Tests grün vor Merge** (`pytest -q`, CI-Check „test").
8. Ein Issue → ein PR, frischer Branch von `master`, kurze PR-Beschreibung mit belegter Ursache.
9. Issue nach dem Merge mit PR-Link schließen; zeigt die nächste Ausgabe den Befund erneut,
   legt der Check ein neues Issue an.
10. Mergen nur nach der Auto-Merge-Regel unten.

## Backlog (Stand 27.11.2026)

Offen aus der Bot-Zeit, nach Nutzen für die Stabilität sortiert:

1. **Reifegrad bei Absicht**: „Gilt ab 1.12" stand bei einem Plan („will … auslaufen lassen");
   richtig wäre „Entwurf". Regel: `ist_absicht` → Reifegrad höchstens „Entwurf". (27.11.)
2. **Schlagzeilen-Abgleich zu streng** für trennbare Verben/Ableitungen („läuft aus" ↔
   „auslaufen", „sinken" ↔ „Senkung"); fiel deshalb 27.11. auf einen schlechteren Titel zurück.
3. **Telegram „4 von 5" (20.11.)**: Ursache nie belegt (Text kam vollständig an). Nur weiter
   verfolgen, wenn es wieder auftritt — dann Screenshot anfordern.
4. GitHub-Issues aus der Anfangszeit: #15 (GLM-Provider), #14 (LLM-as-Judge — widerspricht
   „keine neuen Kosten", eher schließen), #8, #7, #6 (Webapp). Vor Bearbeitung prüfen, ob noch aktuell.

Nicht mehr bauen (siehe CLAUDE.md „Was bewusst NICHT gebaut wird"): Feed, Klick-Tracking,
Zusatz-Pushes außerhalb 06/11/16/20 Uhr.

## Tägliche Claude-Session (eingerichtet 27.11.2026, Entscheidung Unur)

- **Name:** „auf-stand: Qualitäts-Issues abarbeiten"
- **Zeit:** täglich 07:00 Wien (`CRON_TZ=Europe/Vienna 0 7 * * *`)
- **Wo:** geplante Aufgabe im Claude-Code-Konto von Unur (claude.ai → Claude Code →
  geplante Aufgaben); pausieren/löschen dort oder per Claude-Session.
- **Kosten:** nur Kontingent des bestehenden Claude-Abos, kein neues Secret.

Ablauf: Offene Issues mit Label `qualitaetscheck` holen. Hat der GitHub-Cron des
Qualitätschecks (06:40) heute noch nicht geliefert, prüft die Session selbst
(`python -m copilot.main pruefen`) und legt bei Befund das Issue an. Kein offenes Issue →
nichts tun. Sonst je Issue: Ursache belegen, Fix + Regressionstest, PR, Auto-Merge nach
der Regel unten, Issue mit PR-Link schließen.

## Auto-Merge-Regel (Entscheidung Unur, 27.11.2026)

Claude darf einen PR **selbst per Squash mergen**, wenn **alle** Bedingungen erfüllt sind:

1. Alle Checks grün (CI „test" und lokal `pytest -q`).
2. Keine neuen Secrets, keine Secrets/Tokens im Diff.
3. Keine Kosten: keine neuen kostenpflichtigen Dienste oder zusätzlichen API-Aufrufe,
   `requirements*.txt` unverändert.
4. Der Diff passt zum Issue (nur der Fix, sein Test, ggf. Doku) — kein Beifang.
5. **Keine Änderungen unter `.github/`** (Workflows) und nichts an Secrets/Variablen.

Ist eine Bedingung nicht erfüllt, bleibt der PR offen; Claude schreibt ins Issue, welche
Bedingung fehlt — dann entscheidet Unur. Ausnahme Workflow-Änderungen: immer Unur.

## Entscheidungen, die nur Unur treffen kann

- **Geplante Session und Auto-Merge**: entschieden (siehe oben). Zurücknehmen: Aufgabe
  pausieren bzw. diesen Abschnitt ändern.
- **Claude in GitHub Actions** (claude-code-action) wäre möglich, weil `ANTHROPIC_API_KEY`
  schon als Secret existiert — verursacht aber **zusätzliche API-Kosten** pro Lauf. Darum
  nicht eingerichtet.
