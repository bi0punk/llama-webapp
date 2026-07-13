from __future__ import annotations

from app.discovery import scan_model_files
from app.models import Model
from app.queue import queue
from app.repositories.model_repo import (
    bulk_upsert_from_scan,
    create_model,
    delete_model,
    get_model_or_404,
    model_exists,
)
from app.repositories.registry_repo import load_registry
from app.tasks import download_model


def import_local_models() -> int:
    found = scan_model_files()
    return bulk_upsert_from_scan(found)


def enqueue_download(model_id: int) -> int:
    from app.db import session_scope as db_session
    from app.repositories.job_repo import create_job, update_job

    model = get_model_or_404(model_id)
    with db_session() as s:
        db_model = s.get(Model, model_id)
        if db_model:
            db_model.status = "DOWNLOADING"
    job = create_job(type_="download", status="queued", progress=0, message=f"Downloading model {model.id}")
    rq_job = queue.enqueue(download_model, job.id, model_id, job_timeout="12h")
    update_job(job.id, rq_job_id=rq_job.id)
    return job.id


def add_model(name: str, url: str = "", source_type: str = "direct_url") -> Model:
    return create_model(name, url, source_type)


def add_and_download_model(name: str, url: str, source_type: str = "direct_url") -> int:
    model = create_model(name, url, source_type)
    return enqueue_download(model.id)


def import_registry_entries() -> int:
    entries = load_registry()
    count = 0
    for entry in entries:
        name = entry.get("name") or "model.gguf"
        url = entry.get("url")
        if model_exists(name, url):
            continue
        create_model(
            name=name,
            url=url or "",
            source_type=entry.get("source_type", "direct_url"),
        )
        count += 1
    return count


def delete_model_entry(model_id: int) -> None:
    delete_model(model_id)
