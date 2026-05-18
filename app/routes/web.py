from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import HUGGING_FACE_TOKEN
from app.deps import (
    advertised_base_url,
    build_curl_examples,
    get_jobs,
    get_models_page,
    load_registry,
    load_runtime_settings,
    loopback_base_url,
    precompute_profiles,
    templates,
)
from app.discovery import find_llama_binaries, model_scan_roots
from app.llama_server_manager import get_server_status, server_log_tail
from app.system_info import system_snapshot

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return RedirectResponse(url="/server", status_code=302)


@router.get("/server", response_class=HTMLResponse)
def server_page(request: Request):
    settings = load_runtime_settings()
    server_status = get_server_status()
    binaries = find_llama_binaries()
    models, _ = get_models_page(page=1, page_size=500)
    profiles = precompute_profiles(models)
    curl_examples = build_curl_examples()
    return templates.TemplateResponse(
        "server.html",
        {
            "request": request,
            "settings": settings,
            "server_status": server_status,
            "binaries": binaries,
            "models": models,
            "profiles": profiles,
            "curl_examples": curl_examples,
            "log_tail": server_log_tail(),
            "scan_roots": model_scan_roots(),
            "system_info": system_snapshot(),
            "advertised_base_url": advertised_base_url(settings),
            "loopback_base_url": loopback_base_url(settings),
        },
    )


@router.get("/models", response_class=HTMLResponse)
def models_page(request: Request, page: int = 1):
    models, total = get_models_page(page=page)
    profiles = precompute_profiles(models)
    return templates.TemplateResponse(
        "models.html",
        {
            "request": request,
            "models": models,
            "profiles": profiles,
            "jobs": get_jobs(),
            "registry": load_registry(),
            "has_token": bool(HUGGING_FACE_TOKEN),
            "settings": load_runtime_settings(),
            "page": page,
            "total": total,
            "page_size": 100,
        },
    )


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request):
    return templates.TemplateResponse(
        "jobs.html",
        {
            "request": request,
            "jobs": get_jobs(),
        },
    )


@router.get("/playground", response_class=HTMLResponse)
def playground_page(request: Request):
    return templates.TemplateResponse(
        "playground.html",
        {
            "request": request,
            "server_status": get_server_status(),
            "settings": load_runtime_settings(),
            "advertised_base_url": advertised_base_url(load_runtime_settings()),
        },
    )
