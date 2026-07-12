from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.templating import Jinja2Templates
from redis import Redis
from rq import Queue

__all__ = [
    "advertised_base_url",
    "build_curl_examples",
    "enqueue_download",
    "get_jobs",
    "get_model_profile",
    "get_models_page",
    "import_local_models",
    "load_registry",
    "load_runtime_settings",
    "loopback_base_url",
    "precompute_profiles",
    "templates",
]

from app.config import MODELS_PAGE_SIZE, REDIS_PASSWORD, REDIS_URL
from app.db import session_scope
from app.discovery import scan_model_files
from app.llama_server_manager import get_server_status
from app.model_profiles import describe_model
from app.models import Job, Model
from app.runtime_settings import RuntimeSettings, load_runtime_settings
from app.system_info import default_public_host

BASE_DIR = Path(__file__).resolve().parent


def _redis_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if REDIS_PASSWORD:
        kwargs["password"] = REDIS_PASSWORD
    return kwargs


redis_conn = Redis.from_url(REDIS_URL, **_redis_kwargs())
queue = Queue("default", connection=redis_conn)


templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def get_models_page(page: int = 1, page_size: int = MODELS_PAGE_SIZE) -> tuple[list[Model], int]:
    with session_scope() as s:
        total = s.query(Model).count()
        models = s.query(Model).order_by(Model.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return models, total


def get_jobs(limit: int = 50) -> list[Job]:
    with session_scope() as s:
        return s.query(Job).order_by(Job.created_at.desc()).limit(limit).all()


def load_registry() -> list[dict[str, Any]]:
    registry_path = BASE_DIR / "model_registry.json"
    if not registry_path.exists():
        return []
    try:
        entries = json.loads(registry_path.read_text(encoding="utf-8"))
        return entries if isinstance(entries, list) else []
    except Exception:
        return []


def serialize_model(model: Model) -> dict[str, Any]:
    return {
        "id": model.id,
        "name": model.name,
        "status": model.status,
        "local_path": model.local_path,
        "size_bytes": model.size_bytes,
        "url": model.url,
        "source_type": model.source_type,
    }


def loopback_base_url(settings: RuntimeSettings) -> str:
    return f"http://127.0.0.1:{settings.server_port}"


def advertised_base_url(settings: RuntimeSettings) -> str:
    host = settings.public_host or default_public_host()
    port = settings.public_port or settings.server_port
    return f"http://{host}:{port}"


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
        return {
            "health": f"curl -s {base}/health",
            "models": f"curl -s {base}/v1/models {auth_header}".strip(),
            "chat": f"curl -s {base}/v1/chat/completions {joined_headers} -d '{chat_payload}'".strip(),
            "completion": (
                f"curl -s {base}/completion {auth_header} -H 'Content-Type: application/json' -d '{completion_payload}'"
            )
            .replace("  ", " ")
            .strip(),
        }

    return {
        "localhost": build(local_base),
        "lan": build(lan_base),
    }


def precompute_profiles(models: list[Model]) -> dict[int, dict[str, Any]]:
    return {m.id: describe_model(m.local_path or m.name, m.size_bytes) for m in models if m.local_path}


def import_local_models() -> int:
    found = scan_model_files()
    imported = 0

    with session_scope() as s:
        existing_by_path = {m.local_path: m for m in s.query(Model).all() if m.local_path}
        for path in found:
            file_path = Path(path)
            if not file_path.exists():
                continue
            existing = existing_by_path.get(str(file_path))
            if existing:
                existing.name = file_path.name
                existing.status = "READY"
                existing.size_bytes = file_path.stat().st_size
                imported += 1
                continue
            s.add(
                Model(
                    name=file_path.name,
                    source_type="local_scan",
                    local_path=str(file_path),
                    status="READY",
                    size_bytes=file_path.stat().st_size,
                )
            )
            imported += 1
    return imported


def get_model_profile(model_id: int) -> dict[str, Any]:
    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")
        path_or_name = model.local_path or model.name
        return {
            "model_id": model.id,
            "model_name": model.name,
            "local_path": model.local_path,
            "profile": describe_model(path_or_name, model.size_bytes),
        }


def enqueue_download(model_id: int) -> int:
    from app.tasks import download_model

    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        model.status = "DOWNLOADING"
        job = Job(type="download", status="queued", progress=0, message=f"Downloading model {model.id}")
        s.add(job)
        s.flush()
        job_id = job.id

    rq_job = queue.enqueue(download_model, job_id, model_id, job_timeout="12h")
    with session_scope() as s:
        db_job: Job | None = s.get(Job, job_id)
        if db_job:
            db_job.rq_job_id = rq_job.id
    return job_id
