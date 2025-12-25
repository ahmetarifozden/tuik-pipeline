#!/usr/bin/env bash
set -euo pipefail

# Script'in bulunduğu klasöre geç
cd "$(dirname "$0")"

# .env yükle (yoksa hata verme, uyar)
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "[WARN] .env bulunamadı. (İstersen .env.example -> .env kopyala)"
fi

# Poetry kontrol (yoksa anlamlı hata ver)
if ! command -v poetry >/dev/null 2>&1; then
  echo "[ERROR] poetry komutu bulunamadı. Poetry kurulu mu?"
  exit 1
fi

#echo "[INFO] DB tabloları oluşturuluyor..."
#poetry run python -m scripts.create_tables

#echo "[INFO] Kategoriler seed ediliyor..."
#poetry run python -m scripts.seed_categories

#echo "[INFO] Datasetler seed ediliyor..."
#poetry run python -m scripts.seed_datasets

#echo "[INFO] Dataset refresh (opsiyonel)..."
#poetry run python -m scripts.refresh_dataset || true

echo "[INFO] API başlatılıyor: http://127.0.0.1:8000"
exec poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
