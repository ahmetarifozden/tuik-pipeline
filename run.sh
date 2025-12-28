#!/usr/bin/env bash
set -euo pipefail

# Switch to script directory
cd "$(dirname "$0")"

# Load .env
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "[WARN] .env not found."
fi

# Check Poetry
if ! command -v poetry >/dev/null 2>&1; then
  echo "[ERROR] poetry not found."
  exit 1
fi

echo "[INFO] Starting API: http://127.0.0.1:8000"
exec poetry run uvicorn src.tuik_pipeline.main:app --reload --host 0.0.0.0 --port 8000
