#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "================================================="
echo "   Kamera Kişi Sayacı - Otomatik Kurulum"
echo "================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[HATA] python3 bulunamadı. Lütfen sisteminize Python 3.10 veya üzeri yükleyin."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[1/3] Sanal ortam oluşturuluyor (.venv)..."
    python3 -m venv .venv
else
    echo "[1/3] Sanal ortam (.venv) zaten mevcut."
fi

echo "[2/3] Bağımlılıklar yükleniyor..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[3/3] Kurulum başarıyla tamamlandı!"
echo "Programı başlatmak için: ./baslat.sh veya bash baslat.sh"
