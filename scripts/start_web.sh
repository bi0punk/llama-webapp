#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
DATA_DIR_VALUE="${DATA_DIR:-$ROOT_DIR/data}"
REDIS_URL_VALUE="${REDIS_URL:-redis://127.0.0.1:6379/0}"
WEB_HOST_VALUE="${WEB_HOST:-0.0.0.0}"
WEB_PORT_VALUE="${WEB_PORT:-8000}"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "[ERROR] No existe el entorno virtual en $VENV_DIR. Ejecuta primero ./scripts/bootstrap_native_linux.sh"
  exit 1
fi

mkdir -p "$DATA_DIR_VALUE" "$ROOT_DIR/models"
source "$VENV_DIR/bin/activate"
export DATA_DIR="$DATA_DIR_VALUE"
export REDIS_URL="$REDIS_URL_VALUE"
export WEB_HOST="$WEB_HOST_VALUE"
export WEB_PORT="$WEB_PORT_VALUE"
exec python -m uvicorn app.main:app --host "$WEB_HOST" --port "$WEB_PORT" --workers 1
