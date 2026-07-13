from __future__ import annotations

import json

from app.llama_server_manager import get_server_status
from app.runtime_settings import load_runtime_settings
from app.services.url_service import advertised_base_url, loopback_base_url


def build_curl_examples() -> dict[str, dict[str, str]]:
    settings = load_runtime_settings()
    status = get_server_status()
    if status["status"] != "running":
        return {"localhost": {}, "lan": {}}

    local_base = loopback_base_url(settings)
    lan_base = advertised_base_url(settings)
    alias = status.get("state", {}).get("alias") or settings.alias or "llama-local"
    api_key = status.get("state", {}).get("api_key") or settings.api_key

    auth_header = f"-H 'Authorization: Bearer {api_key}'" if api_key else ""
    headers = ["-H 'Content-Type: application/json'"]
    if auth_header:
        headers.insert(0, auth_header)
    joined_headers = " ".join(headers).strip()

    chat_payload = json.dumps(
        {
            "model": alias,
            "messages": [{"role": "user", "content": "Hola, dame un resumen técnico del sistema"}],
            "temperature": 0.2,
        },
        ensure_ascii=False,
    )
    completion_payload = json.dumps(
        {
            "prompt": "Explica en 3 puntos qué hace llama.cpp",
            "n_predict": 128,
        },
        ensure_ascii=False,
    )

    def build(base: str) -> dict[str, str]:
        result: dict[str, str] = {
            "health": f"curl -s {base}/health",
            "models": f"curl -s {base}/v1/models {auth_header}".strip(),
            "chat": f"curl -s {base}/v1/chat/completions {joined_headers} -d '{chat_payload}'".strip(),
        }
        completion = (
            f"curl -s {base}/completion {auth_header} -H 'Content-Type: application/json' -d '{completion_payload}'"
        )
        result["completion"] = completion.replace("  ", " ").strip()
        return result

    return {
        "localhost": build(local_base),
        "lan": build(lan_base),
    }
