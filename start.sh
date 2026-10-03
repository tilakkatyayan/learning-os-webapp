#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
: "${AIRTABLE_TOKEN:?Set AIRTABLE_TOKEN in the shell before starting the Learning OS UI}"
export AIRTABLE_BASE_ID="${AIRTABLE_BASE_ID:-appPgdJLtBMlQluhK}"
export PORT="${PORT:-8000}"
python3 server.py
