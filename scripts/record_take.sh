#!/usr/bin/env bash
# Produce a clean, flat, autonomous green take for the video.
#
# The shared coordination reasoner occasionally spawns a recursive sub-condition (a
# parked capability) that stalls a run. demo_autonomous.py detects that in seconds and
# exits 2 (RECURSED), tearing down its throwaway workspace. This wrapper simply re-runs
# until it gets a clean flat CLOSED (exit 0), which it keeps for you to record.
#
# Run from emily-agent/ with the venv active and control+worker+intel up:
#   ./scripts/record_take.sh
set -uo pipefail
cd "$(dirname "$0")/.."

export EMILY_KEEP=1
export GOOGLE_GENAI_USE_VERTEXAI=FALSE
: "${GOOGLE_API_KEY:=$(grep '^GOOGLE_API_KEY=' ../intel/.env | head -1 | cut -d= -f2- | tr -d '\r"')}"
export GOOGLE_API_KEY

ATTEMPTS="${1:-8}"
for i in $(seq 1 "$ATTEMPTS"); do
  echo "=== take attempt $i/$ATTEMPTS ==="
  python -u scripts/demo_autonomous.py
  rc=$?
  if [ "$rc" -eq 0 ]; then
    echo "=== GREEN take on attempt $i. Record this run (workspace kept). ==="
    exit 0
  fi
  echo "(attempt $i not flat; retrying)"
  sleep 1
done
echo "=== no flat take in $ATTEMPTS attempts; try again ==="
exit 1
