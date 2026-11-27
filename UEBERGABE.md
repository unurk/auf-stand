# Übergabe: Betrieb ohne Bot (ab 1.12.2026)

Bis 30.11.2026 hat ein externer Bot jeden Morgen die 06-Uhr-Ausgabe geprüft,
Aufträge an Claude Code formuliert und die PRs gemergt. Ab 1.12. läuft das so:

| Was | Wer | Kosten / Secret |
|---|---|---|
| Ausgaben erzeugen (4×/Tag) | GitHub Actions `lagebild.yml` — wie bisher | unverändert |
| **Täglich prüfen** (06:40 Wien) | GitHub Actions `qualitaet.yml` → `copilot/pruefung.py` | keine; nur vorhandene Secrets |
| Bei Befund melden | GitHub-Issue (Label `qualitaetscheck`) + Telegram-Alarm | keine |
| **Befund beheben** | Claude Code — von Hand (Einzeiler unten) oder als geplante Session | Claude-Abo, kein neues Secret |
| Mergen | Unur (ein Klick, wenn Checks grün) — oder Auto-Merge, siehe „Entscheidungen" | — |

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
9. Issue erst schließen, wenn der Fix gemergt ist und die nächste Ausgabe den Befund nicht mehr zeigt.

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

## Entscheidungen, die nur Unur treffen kann

- **Tägliche Claude-Session statt Einzeiler** (empfohlen): Eine geplante Claude-Code-Session
  (claude.ai → Claude Code → geplante Aufgaben; auf diesem Konto bereits genutzt) startet
  täglich um ~07:00 mit dem Einzeiler oben. Kostet kein neues Secret, nur Kontingent des
  bestehenden Claude-Abos. Einrichtung: Claude in einer Session bitten „richte die tägliche
  Qualitäts-Session aus UEBERGABE.md ein".
- **Auto-Merge**: Bisher hat der Bot gemergt. Ohne Bot braucht jeder PR einen Klick von Unur.
  Wer auch das abgeben will, erlaubt der geplanten Session ausdrücklich, PRs mit grünen Checks
  per Auto-Merge (squash) zu mergen. Das ist eine bewusste Vertrauensentscheidung —
  standardmäßig mergt Claude **nicht** selbst.
- **Claude in GitHub Actions** (claude-code-action) wäre möglich, weil `ANTHROPIC_API_KEY`
  schon als Secret existiert — verursacht aber **zusätzliche API-Kosten** pro Lauf. Darum
  nicht eingerichtet.
