from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from app.config import (
    DEFAULT_BINARY_CANDIDATES,
    DEFAULT_CTX_SIZE,
    DEFAULT_MODELS_DIR,
    DEFAULT_N_GPU_LAYERS,
    DEFAULT_SERVER_ALIAS,
    DEFAULT_SERVER_HOST,
    DEFAULT_SERVER_PORT,
    DEFAULT_THREADS,
    DEFAULT_PUBLIC_HOST,
    DEFAULT_PUBLIC_PORT,
    SETTINGS_PATH,
)


@dataclass
class RuntimeSettings:
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
    path = Path(SETTINGS_PATH)
    if not path.exists():
        settings = RuntimeSettings()
        save_runtime_settings(settings)
        return settings

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        settings = RuntimeSettings()
        return _apply_payload(settings, payload)
    except Exception:
        settings = RuntimeSettings()
        save_runtime_settings(settings)
        return settings


def save_runtime_settings(settings: RuntimeSettings) -> None:
    path = Path(SETTINGS_PATH)
    os.makedirs(path.parent, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8")


def update_runtime_settings(**kwargs: Any) -> RuntimeSettings:
    settings = load_runtime_settings()
    settings = _apply_payload(settings, kwargs)
    save_runtime_settings(settings)
    return settings
