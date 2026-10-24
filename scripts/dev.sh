#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
exec "$root/.venv/bin/python" "$root/examples/dev_server.py" --state "${LABKG_STATE:-$root/.labkg-dev}" --port "${LABKG_PORT:-8766}" "$@"
