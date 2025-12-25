#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

# .env yükle
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "[WARN] .env bulunamadı"
fi

# Argümanları python'a aynen ilet
poetry run python -m scripts.print_from_config "$@"
