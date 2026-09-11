#!/usr/bin/env bash
cd "$(dirname "$0")"

if [ ! -f ".venv/bin/python" ]; then
    echo "[NOTICE] Virtual environment not found. Starting setup..."
    bash install.sh
fi

echo "Starting application..."
echo "Web Dashboard: http://localhost:8000"

source .venv/bin/activate
python app.py
