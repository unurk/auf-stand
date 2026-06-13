#!/usr/bin/env bash
# Richtet die drei Cron-Trigger auf cron-job.org ein.
# Einmalig ausführen:
#   CRONJOB_KEY=<api-key> GH_TOKEN=<pat> bash scripts/setup_cron.sh
set -euo pipefail

REPO="unurk/auf-stand"
DISPATCH_URL="https://api.github.com/repos/${REPO}/actions/workflows/lagebild.yml/dispatches"

: "${CRONJOB_KEY:?CRONJOB_KEY fehlt — cron-job.org API-Key setzen}"
: "${GH_TOKEN:?GH_TOKEN fehlt — GitHub Fine-grained PAT setzen}"

create_job() {
  local title="$1" hour="$2" minute="$3" wday="$4"
  curl -sf -X PUT "https://api.cron-job.org/jobs" \
    -H "Authorization: Bearer ${CRONJOB_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"job\": {
        \"title\": \"${title}\",
        \"url\": \"${DISPATCH_URL}\",
        \"enabled\": true,
        \"schedule\": {
          \"timezone\": \"UTC\",
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
        \"body\": \"{\\\"ref\\\": \\\"master\\\"}\"
      }
    }"
}

echo "→ Morgen-Ausgabe  (05:00 UTC = 07:00 Wien)..."
create_job "Auf Stand · Morgen"  5 0 "-1"
echo " OK"

echo "→ Abend-Ausgabe   (14:00 UTC = 16:00 Wien)..."
create_job "Auf Stand · Abend"  14 0 "-1"
echo " OK"

echo "→ Wochen-Quittung (07:00 UTC Sa = 09:00 Wien)..."
create_job "Auf Stand · Woche"   7 0 "6"
echo " OK"

echo ""
echo "✓ Alle drei Cron-Jobs angelegt. Auf cron-job.org nachsehen:"
echo "  https://cron-job.org/en/members/jobs/"
