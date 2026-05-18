from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.config import (
    DEFAULT_BINARY_CANDIDATES,
    DEFAULT_CTX_SIZE,
    DEFAULT_MODELS_DIR,
    DEFAULT_N_GPU_LAYERS,
    DEFAULT_PUBLIC_HOST,
    DEFAULT_PUBLIC_PORT,
    DEFAULT_SERVER_ALIAS,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    DEFAULT_THREADS,
    SETTINGS_PATH,
)


class RuntimeSettings(BaseModel):
    model_root_dir: str = DEFAULT_MODELS_DIR
    binary_path: str = DEFAULT_BINARY_CANDIDATES[0]
    server_host: str = DEFAULT_SERVER_HOST
    server_port: int = DEFAULT_SERVER_PORT
    alias: str = DEFAULT_SERVER_ALIAS
    ctx_size: int = DEFAULT_CTX_SIZE
    threads: int = DEFAULT_THREADS
    n_gpu_layers: int = DEFAULT_N_GPU_LAYERS
    api_key: str = ""
    extra_args: str = ""
    public_host: str = DEFAULT_PUBLIC_HOST
    public_port: int = DEFAULT_PUBLIC_PORT
    last_model_id: int | None = None

    model_config = ConfigDict(extra="ignore")


_cache: dict[str, Any] = {"settings": None, "ts": 0.0, "ttl": 1.0}


def _normalize_path(value: str) -> str:
    if not value:
        return value
    return str(Path(value).expanduser().resolve())


def _apply_payload(settings: RuntimeSettings, payload: dict[str, Any]) -> RuntimeSettings:
    for key, value in payload.items():
        if not hasattr(settings, key):
            continue
        if key in {"model_root_dir", "binary_path"} and isinstance(value, str):
            value = _normalize_path(value)
        setattr(settings, key, value)
    return settings


def load_runtime_settings() -> RuntimeSettings:
    now = time.time()
    if _cache["settings"] is not None and (now - _cache["ts"]) < _cache["ttl"]:
        return _cache["settings"]

    path = Path(SETTINGS_PATH)
    if not path.exists():
        settings = RuntimeSettings()
        save_runtime_settings(settings)
        _cache["settings"] = settings
        _cache["ts"] = now
        return settings

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        settings = RuntimeSettings.model_validate(payload)
        _cache["settings"] = settings
        _cache["ts"] = now
        return settings
    except Exception:
        settings = RuntimeSettings()
        save_runtime_settings(settings)
        _cache["settings"] = settings
        _cache["ts"] = now
        return settings


def save_runtime_settings(settings: RuntimeSettings) -> None:
    path = Path(SETTINGS_PATH)
    os.makedirs(path.parent, exist_ok=True)
    path.write_text(
        json.dumps(settings.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _cache["settings"] = settings
    _cache["ts"] = time.time()


def invalidate_cache() -> None:
    _cache["settings"] = None
    _cache["ts"] = 0.0


def update_runtime_settings(**kwargs: Any) -> RuntimeSettings:
    settings = load_runtime_settings()
    settings = _apply_payload(settings, kwargs)
    save_runtime_settings(settings)
    return settings
