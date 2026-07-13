from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from app.config import MODELS_PAGE_SIZE
from app.db import session_scope
from app.models import Model


def get_models_page(page: int = 1, page_size: int = MODELS_PAGE_SIZE) -> tuple[list[Model], int]:
    with session_scope() as s:
        total = s.query(Model).count()
        models = s.query(Model).order_by(Model.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
        return models, total


def get_model_or_404(model_id: int) -> Model:
    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")
        return model


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


def create_model(name: str, url: str = "", source_type: str = "direct_url") -> Model:
    with session_scope() as s:
        model = Model(name=name.strip(), url=url.strip(), source_type=source_type.strip() or "direct_url")
        s.add(model)
        s.flush()
        created = s.get(Model, model.id)
        assert created is not None
        return created


def bulk_upsert_from_scan(found_paths: list[str]) -> int:
    from pathlib import Path

    imported = 0
    with session_scope() as s:
        existing_by_path = {m.local_path: m for m in s.query(Model).all() if m.local_path}
        for path in found_paths:
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


def model_exists(name: str, url: str | None) -> bool:
    with session_scope() as s:
        existing = {(m.name, m.url) for m in s.query(Model).all()}
        return (name, url) in existing


def delete_model(model_id: int) -> None:
    from contextlib import suppress
    from pathlib import Path

    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            return
        if model.local_path:
            with suppress(Exception):
                Path(model.local_path).unlink(missing_ok=True)
        s.delete(model)
