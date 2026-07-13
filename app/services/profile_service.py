from __future__ import annotations

from typing import Any

from app.model_profiles import describe_model
from app.models import Model
from app.repositories.model_repo import get_model_or_404


def precompute_profiles(models: list[Model]) -> dict[int, dict[str, Any]]:
    return {m.id: describe_model(m.local_path or m.name, m.size_bytes) for m in models if m.local_path}


def get_model_profile(model_id: int) -> dict[str, Any]:
    model = get_model_or_404(model_id)
    path_or_name = model.local_path or model.name
    return {
        "model_id": model.id,
        "model_name": model.name,
        "local_path": model.local_path,
        "profile": describe_model(path_or_name, model.size_bytes),
    }
