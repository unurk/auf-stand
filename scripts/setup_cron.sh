#!/usr/bin/env bash
# OPTIONAL: Richtet zusätzliche, besonders pünktliche Trigger auf cron-job.org ein.
#
# Nicht mehr erforderlich: Der Workflow erzeugt die Ausgaben seit dem „Früher
# Trigger + exakte Enthüllung"-Umbau bereits repo-only zuverlässig — die GitHub-
# Crons feuern früh & häufig vor dem Slot, und die Webapp enthüllt das Lagebild
# punktgenau zur Kuratierungszeit. cron-job.org ist nur ein optionaler Booster,
# falls man die Erzeugung noch enger an den Slot legen will.
#
# Warum extern dennoch nützlich: GitHubs interner Schedule-Cron feuert unpünktlich
# (Verspätung bis zu Stunden). Ein externer Dienst stößt den Workflow per
# workflow_dispatch-API an — das startet <1 min.
#
# Legt NEUN Jobs an: 5 für die Presse-Ausgabe (lagebild.yml: vier Tagesausgaben +
# Wochen-Quittung) und 4 für die NYT-Edition (nyt.yml). Alle in der Zeitzone
# Europe/Vienna (ganzjährig pünktlich, kein Sommer-/Winterzeit-Drift). Jeder Job
# benennt die Ausgabe explizit über den `edition`-Input und feuert ~10 min VOR dem
# Slot, damit das Lagebild rechtzeitig deployt ist und zur vollen Stunde enthüllt
# werden kann. NYT ist 2 min versetzt (entzerrt gleichzeitige Pages-Deploys).
# Mehrfach ausführbar (idempotent): vorhandene "Copilot ·"/"NYT ·"-Jobs werden
# zuerst entfernt.
#
# Einrichten (Secrets nur zur Laufzeit, NIE ins Repo committen):
#   CRONJOB_KEY=<cron-job.org-API-Key> GH_TOKEN=<GitHub-Fine-grained-PAT> bash scripts/setup_cron.sh
# Status prüfen (nur Lesen, nur CRONJOB_KEY nötig):
#   CRONJOB_KEY=<cron-job.org-API-Key> bash scripts/setup_cron.sh verify
#
# GH_TOKEN: Fine-grained PAT auf unurk/auf-stand, Permission "Actions: Read and write".
# CRONJOB_KEY: cron-job.org → Account → API keys.
set -euo pipefail

REPO="unurk/auf-stand"
DISPATCH_PRESSE="https://api.github.com/repos/${REPO}/actions/workflows/lagebild.yml/dispatches"
DISPATCH_NYT="https://api.github.com/repos/${REPO}/actions/workflows/nyt.yml/dispatches"
API="https://api.cron-job.org"

ACTION="${1:-setup}"

: "${CRONJOB_KEY:?CRONJOB_KEY fehlt — cron-job.org API-Key setzen}"

# ---------------------------------------------------------------------------
# verify: angelegte Booster-Jobs + (best-effort) letzter Lauf auflisten.
# ---------------------------------------------------------------------------
if [ "$ACTION" = "verify" ] || [ "$ACTION" = "list" ]; then
  echo "→ Booster-Jobs auf cron-job.org:"
  jobs_json=$(curl -sf -H "Authorization: Bearer ${CRONJOB_KEY}" "${API}/jobs" || echo '{"jobs":[]}')
  echo "$jobs_json" | python3 -c '
import sys, json, datetime
data = json.load(sys.stdin)
jobs = [j for j in data.get("jobs", [])
        if str(j.get("title", "")).startswith(("Copilot", "NYT"))]
if not jobs:
    print("  (keine angelegt — `bash scripts/setup_cron.sh` ausfuehren)")
    sys.exit(0)
for j in sorted(jobs, key=lambda x: x.get("title", "")):
    s = j.get("schedule", {}) or {}
    hh = ",".join(str(h) for h in s.get("hours", []))
    mm = ",".join(str(m) for m in s.get("minutes", []))
    tz = s.get("timezone", "?")
    state = "an " if j.get("enabled") else "AUS"
    last = j.get("lastExecution")
    if isinstance(last, (int, float)) and last:
        last = datetime.datetime.utcfromtimestamp(last).strftime("%Y-%m-%d %H:%M UTC")
    else:
        last = "-"
    print("  [" + state + "] " + j.get("title", "").ljust(20)
          + "  " + hh + ":" + mm + " " + tz + "  letzter Lauf: " + str(last))
'
  echo ""
  echo "  Details/History: https://console.cron-job.org/jobs"
  exit 0
fi

: "${GH_TOKEN:?GH_TOKEN fehlt — GitHub Fine-grained PAT setzen}"

# Alte "Copilot ·"/"NYT ·"-Jobs entfernen, damit ein erneuter Lauf keine Duplikate
# erzeugt (ersetzt sauber frühere Jobstände).
echo "→ Vorhandene 'Copilot ·'/'NYT ·'-Jobs aufräumen..."
existing=$(curl -sf -H "Authorization: Bearer ${CRONJOB_KEY}" "${API}/jobs" || echo '{"jobs":[]}')
echo "$existing" \
  | python3 -c 'import sys,json; print("\n".join(str(j["jobId"]) for j in json.load(sys.stdin).get("jobs",[]) if str(j.get("title","")).startswith(("Copilot","NYT"))))' \
  | while read -r jid; do
      [ -n "$jid" ] || continue
      curl -sf -X DELETE -H "Authorization: Bearer ${CRONJOB_KEY}" "${API}/jobs/${jid}" >/dev/null \
        && echo "   gelöscht: Job ${jid}"
    done
echo " OK"

# title, dispatch-url, hour, minute, wday (-1 = täglich; 6 = Samstag), edition
create_job() {
  local title="$1" url="$2" hour="$3" minute="$4" wday="$5" edition="$6"
  curl -sf -X PUT "${API}/jobs" \
    -H "Authorization: Bearer ${CRONJOB_KEY}" \
    -H "Content-Type: application/json" \
    -d "{
      \"job\": {
        \"title\": \"${title}\",
        \"url\": \"${url}\",
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

# Presse-Ausgabe (lagebild.yml): feuert ~10 min vor dem Slot (05:50/10:50/15:50/19:50).
echo "→ Presse · Morgen      (05:50 → Slot 06:00 Wien)..."; create_job "Copilot · Morgen"      "$DISPATCH_PRESSE"  5 50 "-1" morgen;     echo " OK"
echo "→ Presse · Mittag      (10:50 → Slot 11:00 Wien)..."; create_job "Copilot · Mittag"      "$DISPATCH_PRESSE" 10 50 "-1" mittag;     echo " OK"
echo "→ Presse · Nachmittag  (15:50 → Slot 16:00 Wien)..."; create_job "Copilot · Nachmittag"  "$DISPATCH_PRESSE" 15 50 "-1" nachmittag; echo " OK"
echo "→ Presse · Abend       (19:50 → Slot 20:00 Wien)..."; create_job "Copilot · Abend"       "$DISPATCH_PRESSE" 19 50 "-1" abend;      echo " OK"
echo "→ Presse · Woche       (Sa 09:00 Wien)..."          ; create_job "Copilot · Woche"       "$DISPATCH_PRESSE"  9  0 "6"  woche;      echo " OK"

# NYT-Edition (nyt.yml): gleiche Slots, 2 min versetzt (entzerrt Pages-Deploys).
echo "→ NYT · Morning        (05:52 → Slot 06:00 Wien)..."; create_job "NYT · Morning"         "$DISPATCH_NYT"     5 52 "-1" morgen;     echo " OK"
echo "→ NYT · Midday         (10:52 → Slot 11:00 Wien)..."; create_job "NYT · Midday"          "$DISPATCH_NYT"    10 52 "-1" mittag;     echo " OK"
echo "→ NYT · Afternoon      (15:52 → Slot 16:00 Wien)..."; create_job "NYT · Afternoon"       "$DISPATCH_NYT"    15 52 "-1" nachmittag; echo " OK"
echo "→ NYT · Evening        (19:52 → Slot 20:00 Wien)..."; create_job "NYT · Evening"         "$DISPATCH_NYT"    19 52 "-1" abend;      echo " OK"

echo ""
echo "✓ Neun Cron-Jobs angelegt (5 Presse + 4 NYT, Europe/Vienna)."
echo "  Status:  CRONJOB_KEY=… bash scripts/setup_cron.sh verify"
echo "  Konsole: https://console.cron-job.org/jobs"
echo "  Tipp: bei einem Job 'Run now' klicken → in GitHub Actions sollte <1 min ein"
echo "  workflow_dispatch-Lauf erscheinen."
