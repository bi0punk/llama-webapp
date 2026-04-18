#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT_DIR="$ROOT_DIR"
SERVICE_USER="${SERVICE_USER:-${SUDO_USER:-$USER}}"
SERVICE_GROUP="${SERVICE_GROUP:-$(id -gn "$SERVICE_USER")}"  
DATA_DIR_VALUE="${DATA_DIR:-$PROJECT_DIR/data}"
REDIS_URL_VALUE="${REDIS_URL:-redis://127.0.0.1:6379/0}"
WEB_HOST_VALUE="${WEB_HOST:-0.0.0.0}"
WEB_PORT_VALUE="${WEB_PORT:-8000}"
INSTALL_WORKER="${INSTALL_WORKER:-yes}"
SYSTEMD_DIR="/etc/systemd/system"
ENV_FILE="$PROJECT_DIR/deploy/systemd/llm-control-center.env"
WEB_SERVICE_OUT="$SYSTEMD_DIR/llm-control-center-web.service"
WORKER_SERVICE_OUT="$SYSTEMD_DIR/llm-control-center-worker.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "[ERROR] Este script debe ejecutarse con sudo o como root."
  exit 1
fi

if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  echo "[ERROR] El usuario $SERVICE_USER no existe."
  exit 1
fi

mkdir -p "$PROJECT_DIR/deploy/systemd" "$DATA_DIR_VALUE"
chown -R "$SERVICE_USER:$SERVICE_GROUP" "$DATA_DIR_VALUE"

cat > "$ENV_FILE" <<ENV
DATA_DIR=$DATA_DIR_VALUE
REDIS_URL=$REDIS_URL_VALUE
WEB_HOST=$WEB_HOST_VALUE
WEB_PORT=$WEB_PORT_VALUE
ENV
chown "$SERVICE_USER:$SERVICE_GROUP" "$ENV_FILE"
chmod 640 "$ENV_FILE"

cat > "$WEB_SERVICE_OUT" <<UNIT
[Unit]
Description=Llama Control Center Web
After=network-online.target redis-server.service
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$PROJECT_DIR/scripts/start_web.sh
Restart=always
RestartSec=3
KillMode=mixed
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
UNIT

if [ "$INSTALL_WORKER" = "yes" ]; then
  cat > "$WORKER_SERVICE_OUT" <<UNIT
[Unit]
Description=Llama Control Center Worker
After=network-online.target redis-server.service llm-control-center-web.service
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_GROUP
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$ENV_FILE
ExecStart=$PROJECT_DIR/scripts/start_worker.sh
Restart=always
RestartSec=3
KillMode=mixed
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
UNIT
fi

if [ "$INSTALL_WORKER" != "yes" ] && [ -f "$WORKER_SERVICE_OUT" ]; then
  systemctl disable --now llm-control-center-worker.service >/dev/null 2>&1 || true
  rm -f "$WORKER_SERVICE_OUT"
fi

systemctl daemon-reload
systemctl enable llm-control-center-web.service
if [ "$INSTALL_WORKER" = "yes" ]; then
  systemctl enable llm-control-center-worker.service
fi

cat <<INFO

Servicios instalados.

Comandos útiles:
  sudo systemctl start llm-control-center-web
  sudo systemctl restart llm-control-center-web
  sudo systemctl status llm-control-center-web
  sudo journalctl -u llm-control-center-web -f

INFO

if [ "$INSTALL_WORKER" = "yes" ]; then
cat <<INFO
  sudo systemctl start llm-control-center-worker
  sudo systemctl restart llm-control-center-worker
  sudo systemctl status llm-control-center-worker
  sudo journalctl -u llm-control-center-worker -f

INFO
fi
