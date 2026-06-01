#!/usr/bin/env bash
# Lance le pipeline Camille (triage + drafting + notif Yves) sur toutes les boîtes.
#
# Usage :
#   ./scripts/camille_run.sh              # défaut : 25 derniers non-lus
#   ./scripts/camille_run.sh --top 50     # 50 derniers
#   ./scripts/camille_run.sh --no-draft   # triage seul
#
# Logs : ~/.capitalnorvex/camille_runs/
set -euo pipefail

REPO="$HOME/Desktop/capitalnorvex-site"
LOG_DIR="$HOME/.capitalnorvex/camille_runs"
mkdir -p "$LOG_DIR"

TS=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/$TS.log"

echo "📨 Camille run @ $(date)" | tee "$LOG_FILE"
cd "$REPO"

# Lance le pipeline et capture stdout+stderr
python3 -m agents.camille_norvex_counsel run "$@" >> "$LOG_FILE" 2>&1
RC=$?

if [ $RC -eq 0 ]; then
  echo "✅ Run OK ($LOG_FILE)" | tee -a "$LOG_FILE"
else
  echo "❌ Run KO (rc=$RC, $LOG_FILE)" | tee -a "$LOG_FILE"
fi

# Garde seulement les 100 derniers logs (rotation)
ls -t "$LOG_DIR"/*.log 2>/dev/null | tail -n +101 | xargs -r rm -f

exit $RC
