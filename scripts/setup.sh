#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
printf '\nReady. Start the server with: ./scripts/dev.sh\n'
