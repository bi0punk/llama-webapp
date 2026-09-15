from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.llama_server_manager import get_server_status
from app.runtime_settings import load_runtime_settings
from app.services.url_service import loopback_base_url


def build_chat_request(request: Request, payload: dict[str, Any], stream: bool) -> dict[str, Any]:
    settings = load_runtime_settings()
    status = get_server_status()
    if status["status"] != "running":
        raise HTTPException(status_code=400, detail="llama-server no está corriendo")

    api_key_header = request.headers.get("X-Api-Key", "")
    configured_api_key = status.get("state", {}).get("api_key") or settings.api_key
    if configured_api_key and api_key_header != configured_api_key:
        raise HTTPException(status_code=401, detail="API key requerida o inválida")

    base_url = loopback_base_url(settings)
    api_key = configured_api_key
    alias = status.get("state", {}).get("alias") or settings.alias
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "model": alias,
        "messages": payload.get("messages") or [{"role": "user", "content": payload.get("prompt") or "Hola"}],
        "temperature": payload.get("temperature", 0.2),
        "max_tokens": payload.get("max_tokens", 256),
        "stream": stream,
    }
    return {"base_url": base_url, "headers": headers, "body": body}
