#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
exec "$root/.venv/bin/python" "$root/scripts/dev_server.py" --state "${LABKG_STATE:-$HOME/labweb-project-data/runtime}" --port "${LABKG_PORT:-8766}" "$@"
