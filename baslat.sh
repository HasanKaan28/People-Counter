#!/usr/bin/env bash
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/python" ]; then
    echo "[UYARI] Sanal ortam bulunamadı. Kurulum başlatılıyor..."
    bash kurulum.sh
fi

echo "Sistem başlatılıyor..."
echo "Kontrol Paneli: http://localhost:8000"

source .venv/bin/activate
python app.py
