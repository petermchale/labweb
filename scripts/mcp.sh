#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
export LABKG_URL="${LABKG_URL:-http://127.0.0.1:8766}"
export LABKG_TOKEN_FILE="${LABKG_TOKEN_FILE:-${LABKG_STATE:-$HOME/labweb-project-data/runtime}/agent.token}"
if [[ ! -f "$LABKG_TOKEN_FILE" ]]; then
  printf 'Start scripts/dev.sh first; credential file is missing.\n' >&2
  exit 1
fi
exec "$root/.venv/bin/python" -m labkg.mcp_server
