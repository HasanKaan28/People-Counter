#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "================================================="
echo "   AI Camera People Counter - Setup"
echo "================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 not found. Please install Python 3.10 or higher."
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "[1/3] Creating virtual environment (.venv)..."
    python3 -m venv .venv
else
    echo "[1/3] Virtual environment (.venv) already exists."
fi

echo "[2/3] Installing dependencies..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "[3/3] Setup completed successfully!"
echo "To start the application: ./start.sh or bash start.sh"
