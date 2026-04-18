#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
DATA_DIR_VALUE="${DATA_DIR:-$ROOT_DIR/data}"
REDIS_URL_VALUE="${REDIS_URL:-redis://127.0.0.1:6379/0}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] No se encontró $PYTHON_BIN en el sistema."
  exit 1
fi

mkdir -p "$DATA_DIR_VALUE" "$ROOT_DIR/models"

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt

cat <<INFO

Bootstrap completado.

Variables sugeridas:
  export DATA_DIR="$DATA_DIR_VALUE"
  export REDIS_URL="$REDIS_URL_VALUE"

Próximos pasos manuales:
  1) Levantar Redis local si usarás descargas en background.
  2) Ejecutar ./scripts/start_web.sh
  3) Opcional: ejecutar ./scripts/start_worker.sh
  4) Para systemd: sudo ./scripts/install_systemd.sh

INFO
