from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse

from app.db import session_scope
from app.deps import (
    enqueue_download,
    get_model_profile,
    import_local_models,
    load_registry,
    load_runtime_settings,
)
from app.llama_server_manager import start_llama_server, stop_llama_server
from app.model_profiles import describe_model
from app.models import Model
from app.runtime_settings import save_runtime_settings
from app.system_info import default_public_host

router = APIRouter()


@router.post("/settings/save")
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


@router.post("/settings/apply_model_profile")
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


@router.post("/models/scan_local")
def scan_local_models() -> RedirectResponse:
    import_local_models()
    return RedirectResponse(url="/models", status_code=303)


@router.post("/models/add")
def add_model(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form("direct_url"),
):
    with session_scope() as s:
        s.add(Model(name=name.strip(), url=url.strip(), source_type=source_type.strip() or "direct_url"))
    return RedirectResponse(url="/models", status_code=303)


@router.post("/models/import_registry")
def import_registry() -> RedirectResponse:
    entries = load_registry()
    with session_scope() as s:
        existing = {(m.name, m.url) for m in s.query(Model).all()}
        for entry in entries:
            key = (entry.get("name"), entry.get("url"))
            if key in existing:
                continue
            s.add(Model(
                name=entry.get("name") or "model.gguf",
                url=entry.get("url"),
                source_type=entry.get("source_type", "direct_url"),
            ))
    return RedirectResponse(url="/models", status_code=303)


@router.post("/models/add_and_download")
def add_and_download(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form("direct_url"),
) -> RedirectResponse:
    with session_scope() as s:
        model = Model(name=name.strip(), url=url.strip(), source_type=source_type.strip() or "direct_url")
        s.add(model)
        s.flush()
        model_id = model.id
    enqueue_download(model_id)
    return RedirectResponse(url="/models", status_code=303)


@router.post("/models/{model_id}/download")
def download_model_action(model_id: int):
    enqueue_download(model_id)
    return RedirectResponse(url="/models", status_code=303)


@router.post("/models/{model_id}/delete")
def delete_model(model_id: int):
    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            return RedirectResponse(url="/models", status_code=303)

        if model.local_path:
            from contextlib import suppress
            with suppress(Exception):
                Path(model.local_path).unlink(missing_ok=True)
        s.delete(model)
    return RedirectResponse(url="/models", status_code=303)


@router.post("/server/start")
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


@router.post("/server/stop")
def server_stop() -> RedirectResponse:
    stop_llama_server()
    return RedirectResponse(url="/server", status_code=303)
