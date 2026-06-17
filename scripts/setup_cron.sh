#!/usr/bin/env bash
# Richtet die verlässlichen Trigger für Copilot auf cron-job.org ein.
#
# Warum extern: GitHubs interner Schedule-Cron feuert nachweislich unpünktlich
# (8–24 min Verspätung) und lässt die meisten Läufe ganz aus. Ein externer
# Dienst stößt den Workflow per workflow_dispatch-API an — das startet <1 min.
#
# Legt FÜNF Jobs an (vier Tagesausgaben + Wochen-Quittung), je in der Zeitzone
# Europe/Vienna (damit ganzjährig pünktlich, kein Sommer-/Winterzeit-Drift).
# Jeder Job benennt die Ausgabe explizit über den `edition`-Input des Workflows,
# ist also unabhängig von der Uhrzeit-Logik. Mehrfach ausführbar (idempotent):
# vorhandene "Copilot · *"-Jobs werden zuerst entfernt.
#
# Einmalig ausführen (Secrets nur zur Laufzeit, NIE ins Repo committen):
#   CRONJOB_KEY=<cron-job.org-API-Key> GH_TOKEN=<GitHub-Fine-grained-PAT> bash scripts/setup_cron.sh
#
# GH_TOKEN: Fine-grained PAT auf unurk/auf-stand, Permission "Actions: Read and write".
# CRONJOB_KEY: cron-job.org → Account → API keys.
set -euo pipefail

REPO="unurk/auf-stand"
DISPATCH_URL="https://api.github.com/repos/${REPO}/actions/workflows/lagebild.yml/dispatches"
API="https://api.cron-job.org"

: "${CRONJOB_KEY:?CRONJOB_KEY fehlt — cron-job.org API-Key setzen}"
: "${GH_TOKEN:?GH_TOKEN fehlt — GitHub Fine-grained PAT setzen}"

# Alte "Copilot · *"-Jobs entfernen, damit ein erneuter Lauf keine Duplikate erzeugt
# (ersetzt sauber die früheren 2-Ausgaben-Jobs).
echo "→ Vorhandene 'Copilot · *'-Jobs aufräumen..."
existing=$(curl -sf -H "Authorization: Bearer ${CRONJOB_KEY}" "${API}/jobs" || echo '{"jobs":[]}')
echo "$existing" \
  | python3 -c 'import sys,json; print("\n".join(str(j["jobId"]) for j in json.load(sys.stdin).get("jobs",[]) if str(j.get("title","")).startswith("Copilot ·")))' \
  | while read -r jid; do
      [ -n "$jid" ] || continue
      curl -sf -X DELETE -H "Authorization: Bearer ${CRONJOB_KEY}" "${API}/jobs/${jid}" >/dev/null \
        && echo "   gelöscht: Job ${jid}"
    done
echo " OK"

# title, hour, minute, wday (-1 = täglich; 6 = Samstag), edition
create_job() {
  local title="$1" hour="$2" minute="$3" wday="$4" edition="$5"
  curl -sf -X PUT "${API}/jobs" \
    -H "Authorization: Bearer ${CRONJOB_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"job\": {
        \"title\": \"${title}\",
        \"url\": \"${DISPATCH_URL}\",
        \"enabled\": true,
        \"schedule\": {
          \"timezone\": \"Europe/Vienna\",
          \"hours\": [${hour}],
          \"minutes\": [${minute}],
          \"mdays\": [-1],
          \"months\": [-1],
          \"wdays\": [${wday}]
        },
        \"requestMethod\": 1,
        \"headers\": [
          {\"name\": \"Authorization\", \"value\": \"Bearer ${GH_TOKEN}\"},
          {\"name\": \"Content-Type\",  \"value\": \"application/json\"}
        ],
        \"body\": \"{\\\"ref\\\": \\\"master\\\", \\\"inputs\\\": {\\\"edition\\\": \\\"${edition}\\\"}}\"
      }
    }" >/dev/null
}

echo "→ Morgen-Ausgabe      (06:00 Wien)..."; create_job "Copilot · Morgen"      6  0 "-1" morgen;     echo " OK"
echo "→ Mittags-Ausgabe     (11:00 Wien)..."; create_job "Copilot · Mittag"     11  0 "-1" mittag;     echo " OK"
echo "→ Nachmittags-Ausgabe (16:00 Wien)..."; create_job "Copilot · Nachmittag" 16  0 "-1" nachmittag; echo " OK"
echo "→ Abend-Ausgabe       (20:00 Wien)..."; create_job "Copilot · Abend"      20  0 "-1" abend;      echo " OK"
echo "→ Wochen-Quittung     (Sa 09:00 Wien)..."; create_job "Copilot · Woche"    9  0 "6"  woche;      echo " OK"

echo ""
echo "✓ Fünf Cron-Jobs angelegt (Europe/Vienna). Auf cron-job.org nachsehen:"
echo "  https://console.cron-job.org/jobs"
echo "  Tipp: bei einem Job 'Run now' klicken → in GitHub Actions sollte <1 min ein"
echo "  workflow_dispatch-Lauf erscheinen."
