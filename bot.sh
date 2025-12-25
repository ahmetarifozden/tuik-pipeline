#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# .env zorunlu olsun
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "❌ .env bulunamadı. .env.example -> .env kopyalayıp DATABASE_URL ayarla."
  exit 1
fi

# DATABASE_URL kontrolü
if [ -z "${DATABASE_URL:-}" ] && [ -z "${DATABASE_URI:-}" ]; then
  echo "❌ DATABASE_URL veya DATABASE_URI set değil (.env içinde olmalı)."
  exit 1
fi

DB_CONTAINER="tuik-pipeline-db-1"

echo "==> [0/3] Docker DB kontrol ediliyor..."
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
  echo "❌ DB container çalışmıyor: ${DB_CONTAINER}"
  echo "👉 Önce: docker compose up -d"
  exit 1
fi
echo "✅ DB container çalışıyor."

echo "==> [1/3] Ana kategoriler çekiliyor (categories.yaml)"
poetry run python -m scripts.fetch_categories

echo "==> [2/3] Dataset'ler DB'ye yazılıyor (seed_datasets)"
poetry run python -m scripts.seed_datasets

echo "✅ DONE: Kategoriler çekildi ve dataset DB güncellendi."
