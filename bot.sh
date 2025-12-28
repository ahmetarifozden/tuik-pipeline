#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# Require .env
if [ -f .env ]; then
  set -a
  source .env
  set +a
else
  echo "❌ .env not found. Please copy .env.example -> .env and set DATABASE_URL."
  exit 1
fi

# Check DATABASE_URL
if [ -z "${DATABASE_URL:-}" ] && [ -z "${DATABASE_URI:-}" ]; then
  echo "❌ DATABASE_URL or DATABASE_URI is not set (must be in .env)."
  exit 1
fi

DB_CONTAINER="tuik-pipeline-db-1"

echo "==> [0/3] Checking Docker DB..."
if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
  echo "❌ DB container is not running: ${DB_CONTAINER}"
  echo "👉 First run: docker compose up -d"
  exit 1
fi
echo "✅ DB container is running."

echo "==> [1/3] Fetching main categories (categories.yaml)"
poetry run python -m scripts.fetch_categories

echo "==> [2/3] Seeding datasets to DB (seed_datasets)"
poetry run python -m scripts.seed_datasets

echo "✅ DONE: Categories fetched and datasets updated in DB."
