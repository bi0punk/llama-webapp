from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LLAMA_",
        extra="ignore",
    )

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

    @field_validator("server_port", "public_port")
    @classmethod
    def _valid_port(cls, v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v

    @field_validator("ctx_size")
    @classmethod
    def _valid_ctx_size(cls, v: int) -> int:
        if v < 512:
            raise ValueError(f"ctx_size must be >= 512, got {v}")
        if v & (v - 1) != 0:
            raise ValueError(f"ctx_size must be a power of 2, got {v}")
        return v

    @field_validator("threads")
    @classmethod
    def _valid_threads(cls, v: int) -> int:
        if v < 1:
            raise ValueError(f"threads must be >= 1, got {v}")
        if v > 256:
            raise ValueError(f"threads must be <= 256, got {v}")
        return v

    @field_validator("n_gpu_layers")
    @classmethod
    def _valid_gpu_layers(cls, v: int) -> int:
        if v < 0:
            raise ValueError(f"n_gpu_layers must be >= 0, got {v}")
        return v


_settings_cache: RuntimeSettings | None = None


def _normalize_path(value: str) -> str:
    if not value:
        return value
    return str(Path(value).expanduser().resolve())


def load_runtime_settings() -> RuntimeSettings:
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache

    base = RuntimeSettings()
    path = Path(SETTINGS_PATH)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for key, value in data.items():
                if hasattr(base, key):
                    if key in {"model_root_dir", "binary_path"} and isinstance(value, str):
                        value = _normalize_path(value)
                    setattr(base, key, value)
        except Exception:
            pass

    _settings_cache = base
    return base


def save_runtime_settings(settings: RuntimeSettings) -> None:
    global _settings_cache
    _settings_cache = settings
    path = Path(SETTINGS_PATH)
    os.makedirs(path.parent, exist_ok=True)
    path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")


def invalidate_cache() -> None:
    global _settings_cache
    _settings_cache = None


def update_runtime_settings(**kwargs: Any) -> RuntimeSettings:
    settings = load_runtime_settings()
    for key, value in kwargs.items():
        if hasattr(settings, key):
            if key in {"model_root_dir", "binary_path"} and isinstance(value, str):
                value = _normalize_path(value)
            setattr(settings, key, value)
    save_runtime_settings(settings)
    return settings
