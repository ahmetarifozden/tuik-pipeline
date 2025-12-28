#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# Load .env
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "[WARN] .env not found."
fi

if [ $# -lt 1 ]; then
  echo "Usage: ./run_config.sh <keyword> [extra_args]"
  exit 1
fi

KW="$1"
shift || true

echo "[STEP 1] DOWNLOAD + manifest: $KW"

# Ensure clean slate: remove old manifest for this keyword if exists
MANIFEST_PATH="downloads/${KW}/manifest.csv"
if [ -f "$MANIFEST_PATH" ]; then
    rm "$MANIFEST_PATH"
fi

poetry run python -m scripts.print_from_config "$KW" "$@"

# Check if manifest exists
if [ ! -f "$MANIFEST_PATH" ]; then
  echo "[INFO] Manifest not found at: $MANIFEST_PATH"
  echo "[INFO] This usually means the download was cancelled or yielded no results."
  echo "[INFO] Pipeline stopped."
  exit 0
fi

echo "[STEP 2] NORMALIZE from manifest: $MANIFEST_PATH"
poetry run python -m scripts.normalize_from_manifest "$MANIFEST_PATH"

echo "[STEP 3] LOAD to DB: normalized/$KW"
poetry run python -m scripts.load_observations "normalized/$KW"

echo "[DONE] Pipeline finished for: $KW"
