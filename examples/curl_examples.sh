#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8081}"
MODEL_ALIAS="${MODEL_ALIAS:-llama-local}"
API_KEY="${API_KEY:-}"

AUTH_ARGS=()
if [[ -n "$API_KEY" ]]; then
  AUTH_ARGS=(-H "Authorization: Bearer $API_KEY")
fi

echo "[1] health"
curl -s "$BASE_URL/health" "${AUTH_ARGS[@]}" || true
printf '\n\n'

echo "[2] models"
curl -s "$BASE_URL/v1/models" "${AUTH_ARGS[@]}" || true
printf '\n\n'

echo "[3] chat completions"
curl -s "$BASE_URL/v1/chat/completions" \
  "${AUTH_ARGS[@]}" \
  -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL_ALIAS\",\"messages\":[{\"role\":\"user\",\"content\":\"Hola, responde en 3 puntos técnicos\"}],\"temperature\":0.2}" || true
printf '\n'
