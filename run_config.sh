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

if [ $# -lt 1 ]; then
  echo "Kullanım: ./run_config.sh <keyword> [ek_argumanlar]"
  exit 1
fi

KW="$1"
shift || true

echo "[STEP 1] DOWNLOAD + manifest: $KW"
poetry run python -m scripts.print_from_config "$KW" "$@"

MANIFEST="downloads/${KW}/manifest.csv"
if [ ! -f "$MANIFEST" ]; then
  echo "[ERROR] manifest bulunamadı: $MANIFEST"
  echo "print_from_config manifest üretmedi veya klasör adı farklı."
  exit 1
fi

echo "[STEP 2] NORMALIZE from manifest: $MANIFEST"
poetry run python -m scripts.normalize_from_manifest "$MANIFEST"

echo "[STEP 3] LOAD to DB: normalized/$KW"
poetry run python -m scripts.load_observations "normalized/$KW"

echo "[DONE] Pipeline bitti: $KW"
