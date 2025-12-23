#!/usr/bin/env bash
set -e  # herhangi bir hata olursa script dursun

# ----------------------------
# Kullanım kontrolü
# ----------------------------
if [ -z "$1" ]; then
  echo "Kullanim:"
  echo "  ./run_keyword.sh <anahtar_kelime>"
  echo "Ornek:"
  echo "  ./run_keyword.sh ciro"
  exit 1
fi

KEYWORD="$1"

echo "=============================================="
echo "TUIK PIPELINE BASLIYOR"
echo "KEYWORD: $KEYWORD"
echo "=============================================="

# ----------------------------
# 1) Bültenleri topla
# ----------------------------
echo ""
echo "[1/2] Bültenler toplanıyor..."
poetry run python scripts/bulten_collect.py "$KEYWORD"

# ----------------------------
# 2) Download linklerini topla
# ----------------------------
echo ""
echo "[2/2] Excel / download linkleri toplanıyor..."
poetry run python scripts/bulten_download_collect.py

echo ""
echo "=============================================="
echo "PIPELINE TAMAMLANDI"
echo "Cikti dosyalari:"
echo " - config/bulten.yaml"
echo " - config/downloads.yaml"
echo "=============================================="
