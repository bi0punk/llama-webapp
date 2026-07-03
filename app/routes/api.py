from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from app.config import DATA_DIR, LOGS_DIR
from app.db import session_scope
from app.deps import (
    advertised_base_url,
    build_curl_examples,
    get_jobs,
    get_model_profile,
    get_models_page,
    load_runtime_settings,
    loopback_base_url,
    precompute_profiles,
    templates,
)
from app.discovery import find_llama_binaries, model_scan_roots, scan_model_files
from app.llama_server_manager import get_server_status, server_log_tail
from app.models import Job
from app.system_info import system_snapshot

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    from sqlalchemy import text

    from app.llama_server_manager import get_server_status

    status = get_server_status()
    db_ok = True
    try:
        with session_scope() as s:
            s.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return JSONResponse(
        {
            "status": "ok",
            "server_status": status["status"],
            "model_loaded": status.get("state", {}).get("model_path"),
            "db_ok": db_ok,
            "data_dir": DATA_DIR,
            "logs_dir": LOGS_DIR,
        }
    )


@router.get("/partials/jobs_table", response_class=HTMLResponse)
def jobs_table_partial(request: Request):
    return templates.TemplateResponse(request, "partials/jobs_table.html", {"jobs": get_jobs()})


@router.get("/partials/models_table", response_class=HTMLResponse)
def models_table_partial(request: Request):
    models, _ = get_models_page(page=1, page_size=500)
    profiles = precompute_profiles(models)
    return templates.TemplateResponse(
        request,
        "partials/models_table.html",
        {
            "models": models,
            "profiles": profiles,
        },
    )


@router.get("/api/server/status")
def api_server_status() -> JSONResponse:
    settings = load_runtime_settings()
    status = get_server_status()
    status["advertised_base_url"] = advertised_base_url(settings)
    status["loopback_base_url"] = loopback_base_url(settings)
    return JSONResponse(status)


@router.get("/api/server/log_tail")
def api_server_log_tail(lines: int = 150) -> JSONResponse:
    return JSONResponse({"tail": server_log_tail(lines=lines)})


@router.get("/api/system/discovery")
def api_system_discovery() -> JSONResponse:
    return JSONResponse(
        {
            "binaries": find_llama_binaries(),
            "scan_roots": model_scan_roots(),
            "models_found": scan_model_files(),
            "system": system_snapshot(),
        }
    )


@router.get("/api/curl_examples")
def api_curl_examples() -> JSONResponse:
    return JSONResponse(build_curl_examples())


@router.get("/api/models/{model_id}/profile")
def api_model_profile(model_id: int) -> JSONResponse:
    return JSONResponse(get_model_profile(model_id))


@router.get("/server/log", response_class=PlainTextResponse)
def server_log() -> PlainTextResponse:
    return PlainTextResponse(server_log_tail())


@router.get("/jobs/{job_id}/log", response_class=PlainTextResponse)
def job_log(job_id: int):
    with session_scope() as s:
        job = s.get(Job, job_id)
        if not job or not job.log_path:
            return PlainTextResponse("No log available.")
        path = Path(job.log_path)
        if not path.exists():
            return PlainTextResponse("Log file not found.")
        text = path.read_text(encoding="utf-8", errors="ignore")
        return PlainTextResponse("\n".join(text.splitlines()[-250:]) + "\n")


@router.post("/api/playground/chat")
def api_playground_chat(payload: dict[str, Any]) -> JSONResponse:
    settings = load_runtime_settings()
    status = get_server_status()
    if status["status"] != "running":
        raise HTTPException(status_code=400, detail="llama-server no está corriendo")

    base_url = loopback_base_url(settings)
    api_key = status.get("state", {}).get("api_key") or settings.api_key
    alias = status.get("state", {}).get("alias") or settings.alias
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    body = {
        "model": alias,
        "messages": payload.get("messages") or [{"role": "user", "content": payload.get("prompt") or "Hola"}],
        "temperature": payload.get("temperature", 0.2),
        "max_tokens": payload.get("max_tokens", 256),
        "stream": False,
    }

    try:
        response = requests.post(f"{base_url}/v1/chat/completions", headers=headers, json=body, timeout=120)
        try:
            payload = response.json()
        except Exception:
            payload = {"raw": response.text}
        return JSONResponse(status_code=response.status_code, content=payload)
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Error consultando llama-server: {exc}") from exc
