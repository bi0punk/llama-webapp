from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis import Redis
from rq import Queue

from app.config import DATA_DIR, HUGGING_FACE_TOKEN, LOGS_DIR, REDIS_URL, WEB_TITLE
from app.db import engine, session_scope
from app.discovery import find_llama_binaries, model_scan_roots, scan_model_files
from app.llama_server_manager import (
    get_server_status,
    server_log_tail,
    start_llama_server,
    stop_llama_server,
)
from app.model_profiles import describe_model
from app.models import Base, Job, Model
from app.runtime_settings import RuntimeSettings, load_runtime_settings, save_runtime_settings
from app.system_info import default_public_host, system_snapshot
from app.tasks import download_model

app = FastAPI(title=WEB_TITLE)
BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

redis_conn = Redis.from_url(REDIS_URL)
queue = Queue("default", connection=redis_conn)


@app.on_event("startup")
def startup() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    settings = load_runtime_settings()
    if not settings.public_host:
        settings.public_host = default_public_host()
        save_runtime_settings(settings)


# ---------------- helpers ----------------

def get_models() -> list[Model]:
    with session_scope() as s:
        return s.query(Model).order_by(Model.created_at.desc()).all()



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
            ).replace("  ", " ").strip(),
        }

    return {
        "localhost": build(local_base),
        "lan": build(lan_base),
    }



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


# ---------------- pages ----------------

@app.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return RedirectResponse(url="/server", status_code=302)


@app.get("/server", response_class=HTMLResponse)
def server_page(request: Request):
    settings = load_runtime_settings()
    server_status = get_server_status()
    binaries = find_llama_binaries()
    models = get_models()
    profiles = {
        m.id: describe_model(m.local_path or m.name, m.size_bytes)
        for m in models
        if m.local_path
    }
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


@app.get("/models", response_class=HTMLResponse)
def models_page(request: Request):
    models = get_models()
    profiles = {
        m.id: describe_model(m.local_path or m.name, m.size_bytes)
        for m in models
        if m.local_path
    }
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
        },
    )


@app.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request):
    return templates.TemplateResponse(
        "jobs.html",
        {
            "request": request,
            "jobs": get_jobs(),
        },
    )


@app.get("/playground", response_class=HTMLResponse)
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


# ---------------- actions ----------------

@app.post("/settings/save")
def save_settings(
    binary_path: str = Form(...),
    model_root_dir: str = Form(...),
    server_host: str = Form(...),
    server_port: int = Form(...),
    public_host: str = Form(""),
    public_port: int = Form(...),
    alias: str = Form(...),
    ctx_size: int = Form(...),
    threads: int = Form(...),
    n_gpu_layers: int = Form(0),
    api_key: str = Form(""),
    extra_args: str = Form(""),
) -> RedirectResponse:
    settings = load_runtime_settings()
    settings.binary_path = str(Path(binary_path.strip()).expanduser())
    settings.model_root_dir = str(Path(model_root_dir.strip()).expanduser())
    settings.server_host = server_host.strip() or "0.0.0.0"
    settings.server_port = int(server_port)
    settings.public_host = public_host.strip() or default_public_host()
    settings.public_port = int(public_port)
    settings.alias = alias.strip() or "llama-local"
    settings.ctx_size = int(ctx_size)
    settings.threads = int(threads)
    settings.n_gpu_layers = int(n_gpu_layers)
    settings.api_key = api_key.strip()
    settings.extra_args = extra_args.strip()
    save_runtime_settings(settings)
    return RedirectResponse(url="/server", status_code=303)


@app.post("/settings/apply_model_profile")
def apply_model_profile(model_id: int = Form(...)) -> RedirectResponse:
    payload = get_model_profile(model_id)
    profile = payload["profile"]
    settings = load_runtime_settings()
    settings.ctx_size = int(profile["ctx_size"])
    settings.threads = int(profile["threads"])
    settings.n_gpu_layers = int(profile["n_gpu_layers"])
    settings.extra_args = profile["extra_args"]
    save_runtime_settings(settings)
    return RedirectResponse(url="/server", status_code=303)


@app.post("/models/scan_local")
def scan_local_models() -> RedirectResponse:
    import_local_models()
    return RedirectResponse(url="/models", status_code=303)


@app.post("/models/add")
def add_model(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form("direct_url"),
):
    with session_scope() as s:
        s.add(Model(name=name.strip(), url=url.strip(), source_type=source_type.strip() or "direct_url"))
    return RedirectResponse(url="/models", status_code=303)


@app.post("/models/import_registry")
def import_registry() -> RedirectResponse:
    entries = load_registry()
    with session_scope() as s:
        existing = {(m.name, m.url) for m in s.query(Model).all()}
        for entry in entries:
            key = (entry.get("name"), entry.get("url"))
            if key in existing:
                continue
            s.add(Model(name=entry.get("name") or "model.gguf", url=entry.get("url"), source_type=entry.get("source_type", "direct_url")))
    return RedirectResponse(url="/models", status_code=303)


@app.post("/models/add_and_download")
def add_and_download(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form("direct_url"),
) -> RedirectResponse:
    with session_scope() as s:
        model = Model(name=name.strip(), url=url.strip(), source_type=source_type.strip() or "direct_url")
        s.add(model)
        s.flush()
        model.status = "DOWNLOADING"
        job = Job(type="download", status="queued", progress=0, message=f"Downloading model {model.id}")
        s.add(job)
        s.flush()
        model_id = model.id
        job_id = job.id

    rq_job = queue.enqueue(download_model, job_id, model_id, job_timeout="12h")
    with session_scope() as s:
        job = s.get(Job, job_id)
        if job:
            job.rq_job_id = rq_job.id
    return RedirectResponse(url="/models", status_code=303)


@app.post("/models/{model_id}/download")
def download_model_action(model_id: int):
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
        job = s.get(Job, job_id)
        if job:
            job.rq_job_id = rq_job.id
    return RedirectResponse(url="/models", status_code=303)


@app.post("/models/{model_id}/delete")
def delete_model(model_id: int):
    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            return RedirectResponse(url="/models", status_code=303)

        if model.local_path:
            try:
                Path(model.local_path).unlink(missing_ok=True)
            except Exception:
                pass
        s.delete(model)
    return RedirectResponse(url="/models", status_code=303)


@app.post("/server/start")
def server_start(
    model_id: int = Form(...),
    apply_recommendation: str | None = Form(None),
) -> RedirectResponse:
    settings = load_runtime_settings()
    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")
        if not model.local_path or not Path(model.local_path).exists():
            raise HTTPException(status_code=400, detail="El modelo no existe en disco. Importa o descarga primero.")
        model_local_path = model.local_path
        model_size = model.size_bytes
        model_name = model.name

    binary_path = Path(settings.binary_path).expanduser()
    if not binary_path.exists():
        raise HTTPException(status_code=400, detail=f"Binario no encontrado: {binary_path}")

    effective_settings = settings
    if apply_recommendation:
        profile = describe_model(model_local_path or model_name, model_size)
        effective_settings.ctx_size = int(profile["ctx_size"])
        effective_settings.threads = int(profile["threads"])
        effective_settings.n_gpu_layers = int(profile["n_gpu_layers"])
        effective_settings.extra_args = profile["extra_args"]
        save_runtime_settings(effective_settings)

    try:
        state = start_llama_server(str(binary_path), model_local_path, effective_settings, model_id=model_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    settings.last_model_id = model_id
    save_runtime_settings(settings)
    if not state:
        raise HTTPException(status_code=500, detail="No se pudo iniciar llama-server")
    return RedirectResponse(url="/server", status_code=303)


@app.post("/server/stop")
def server_stop() -> RedirectResponse:
    stop_llama_server()
    return RedirectResponse(url="/server", status_code=303)


# ---------------- partials / apis ----------------

@app.get("/partials/jobs_table", response_class=HTMLResponse)
def jobs_table_partial(request: Request):
    return templates.TemplateResponse("partials/jobs_table.html", {"request": request, "jobs": get_jobs()})


@app.get("/partials/models_table", response_class=HTMLResponse)
def models_table_partial(request: Request):
    models = get_models()
    profiles = {m.id: describe_model(m.local_path or m.name, m.size_bytes) for m in models if m.local_path}
    return templates.TemplateResponse(
        "partials/models_table.html",
        {
            "request": request,
            "models": models,
            "profiles": profiles,
        },
    )


@app.get("/api/server/status")
def api_server_status() -> JSONResponse:
    settings = load_runtime_settings()
    status = get_server_status()
    status["advertised_base_url"] = advertised_base_url(settings)
    status["loopback_base_url"] = loopback_base_url(settings)
    return JSONResponse(status)


@app.get("/api/server/log_tail")
def api_server_log_tail(lines: int = 150) -> JSONResponse:
    return JSONResponse({"tail": server_log_tail(lines=lines)})


@app.get("/api/system/discovery")
def api_system_discovery() -> JSONResponse:
    return JSONResponse({
        "binaries": find_llama_binaries(),
        "scan_roots": model_scan_roots(),
        "models_found": scan_model_files(),
        "system": system_snapshot(),
    })


@app.get("/api/curl_examples")
def api_curl_examples() -> JSONResponse:
    return JSONResponse(build_curl_examples())


@app.get("/api/models/{model_id}/profile")
def api_model_profile(model_id: int) -> JSONResponse:
    return JSONResponse(get_model_profile(model_id))


@app.get("/server/log", response_class=PlainTextResponse)
def server_log() -> PlainTextResponse:
    return PlainTextResponse(server_log_tail())


@app.get("/jobs/{job_id}/log", response_class=PlainTextResponse)
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


@app.post("/api/playground/chat")
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


if __name__ == "__main__":
    import uvicorn

    web_host = os.getenv("WEB_HOST", "0.0.0.0")
    web_port = int(os.getenv("WEB_PORT", "8000"))
    uvicorn.run("app.main:app", host=web_host, port=web_port, reload=False)
