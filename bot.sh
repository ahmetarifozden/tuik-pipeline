#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

DB_CONTAINER="tuik-pipeline-db-1"

echo "==> [0/3] Docker DB kontrol ediliyor..."

if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
  echo "❌ DB container çalışmıyor: ${DB_CONTAINER}"
  echo "👉 Önce çalıştır:"
  echo "   docker compose up -d"
  exit 1
fi

echo "✅ DB container çalışıyor."

echo "==> [1/3] Ana kategoriler çekiliyor (categories.yaml)"
poetry run python -m scripts.fetch_categories

echo "==> [2/3] Dataset'ler DB'ye yazılıyor (seed_datasets)"
poetry run python -m scripts.seed_datasets

echo "✅ DONE: Kategoriler çekildi ve dataset DB güncellendi."
