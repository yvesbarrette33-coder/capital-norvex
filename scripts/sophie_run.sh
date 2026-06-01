#!/usr/bin/env bash
# Lance le pipeline Sophie (triage + drafting + auto-send + notif Yves) sur info@.
#
# Usage :
#   ./scripts/sophie_run.sh              # défaut : 25 derniers non-lus
#   ./scripts/sophie_run.sh --top 50     # 50 derniers
#   ./scripts/sophie_run.sh --no-draft   # triage seul
#
# Logs : ~/.capitalnorvex/sophie_runs/
set -euo pipefail

REPO="$HOME/Desktop/capitalnorvex-site"
ENV_FILE="$HOME/.capitalnorvex/.env"
LOG_DIR="$HOME/.capitalnorvex/sophie_runs"
mkdir -p "$LOG_DIR"

TS=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="$LOG_DIR/$TS.log"

echo "👋 Sophie run @ $(date)" | tee "$LOG_FILE"

# Charge les variables d'environnement (ANTHROPIC_API_KEY, AZURE_*, etc.)
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
else
  echo "❌ .env manquant: $ENV_FILE" | tee -a "$LOG_FILE"
  exit 1
fi

cd "$REPO"

# Lance le pipeline et capture stdout+stderr
python3 -m agents.sophie_norvex_relations run "$@" >> "$LOG_FILE" 2>&1
RC=$?

if [ $RC -eq 0 ]; then
  echo "✅ Run OK ($LOG_FILE)" | tee -a "$LOG_FILE"
else
  echo "❌ Run KO (rc=$RC, $LOG_FILE)" | tee -a "$LOG_FILE"
fi

# Garde seulement les 100 derniers logs (rotation)
ls -t "$LOG_DIR"/*.log 2>/dev/null | tail -n +101 | xargs -I{} rm -f {}

exit $RC
