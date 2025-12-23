#!/usr/bin/env bash
set -euo pipefail

# Script nereden çağrılırsa çağrılsın proje köküne geç
cd "$(dirname "$0")"

# .env yükle
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "[WARN] .env bulunamadı"
fi

echo "[INFO] config/crawl.yaml okunuyor..."
echo

# Sadece terminale basan Python scripti çalıştır
poetry run python -m scripts.print_from_config

echo
echo "[DONE] Listeleme tamamlandı"
