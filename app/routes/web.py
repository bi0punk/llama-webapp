from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.config import HUGGING_FACE_TOKEN
from app.discovery import model_scan_roots
from app.llama_server_manager import get_server_status, server_log_tail
from app.repositories.job_repo import get_jobs
from app.repositories.model_repo import get_models_page
from app.repositories.registry_repo import load_registry
from app.runtime_settings import load_runtime_settings
from app.services.binary_service import find_llama_binaries
from app.services.curl_service import build_curl_examples
from app.services.profile_preset_service import load_presets
from app.services.profile_service import precompute_profiles
from app.services.url_service import advertised_base_url, loopback_base_url
from app.system_info import system_snapshot
from app.templates import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return RedirectResponse(url="/server", status_code=302)


@router.get("/server", response_class=HTMLResponse)
def server_page(request: Request) -> HTMLResponse:
    settings = load_runtime_settings()
    server_status = get_server_status()
    binaries = find_llama_binaries()
    models, _ = get_models_page(page=1, page_size=500)
    profiles = precompute_profiles(models)
    curl_examples = build_curl_examples()
    return templates.TemplateResponse(
        request,
        "server.html",
        {
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
            "presets": load_presets(),
        },
    )


@router.get("/models", response_class=HTMLResponse)
def models_page(request: Request, page: int = 1) -> HTMLResponse:
    models, total = get_models_page(page=page)
    profiles = precompute_profiles(models)
    return templates.TemplateResponse(
        request,
        "models.html",
        {
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
def jobs_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "jobs.html",
        {
            "jobs": get_jobs(),
        },
    )


@router.get("/playground", response_class=HTMLResponse)
def playground_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "playground.html",
        {
            "server_status": get_server_status(),
            "settings": load_runtime_settings(),
            "advertised_base_url": advertised_base_url(load_runtime_settings()),
        },
    )
