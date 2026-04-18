from __future__ import annotations

import os
from pathlib import Path


def env(key: str, default: str | None = None) -> str:
    value = os.getenv(key)
    if value is None or value == "":
        return "" if default is None else default
    return value


DATA_DIR = env("DATA_DIR", "/data")
DATABASE_URL = env("DATABASE_URL", f"sqlite:///{DATA_DIR}/app.db")
REDIS_URL = env("REDIS_URL", "redis://redis:6379/0")
HUGGING_FACE_TOKEN = env("HUGGING_FACE_TOKEN", "")

DEFAULT_MODELS_DIR = env("DEFAULT_MODELS_DIR", os.path.join(DATA_DIR, "models"))
LOGS_DIR = env("LOGS_DIR", os.path.join(DATA_DIR, "logs"))
SETTINGS_PATH = env("SETTINGS_PATH", os.path.join(DATA_DIR, "runtime_settings.json"))
SERVER_STATE_PATH = env("SERVER_STATE_PATH", os.path.join(DATA_DIR, "llama_server_state.json"))

LLAMA_RUN_BIN = env("LLAMA_RUN_BIN", "/opt/llama/bin/llama-run")
LLAMA_CLI_BIN = env("LLAMA_CLI_BIN", "/opt/llama/bin/llama-cli")
LLAMA_SERVER_BIN = env("LLAMA_SERVER_BIN", "/opt/llama/bin/llama-server")

DEFAULT_BINARY_CANDIDATES = [
    LLAMA_SERVER_BIN,
    LLAMA_RUN_BIN,
    LLAMA_CLI_BIN,
    "/usr/local/bin/llama-server",
    "/usr/bin/llama-server",
    "/usr/local/bin/llama-run",
    "/usr/bin/llama-run",
    "/usr/local/bin/llama-cli",
    "/usr/bin/llama-cli",
]

DEFAULT_LLAMA_SEARCH_PATHS = [
    "/opt/llama/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    str(Path.home() / "opt" / "llama.cpp" / "build" / "bin"),
    str(Path.home() / "llama.cpp" / "build" / "bin"),
    str(Path.home() / ".local" / "bin"),
]

DEFAULT_MODEL_SCAN_PATHS = [
    DEFAULT_MODELS_DIR,
    "/models",
    "/app/models",
    str(Path.home() / "models"),
    str(Path.home() / "Modelos"),
]

EXTRA_LLAMA_SEARCH_PATHS = [p for p in env("LLAMA_SEARCH_PATHS", "").split(":") if p]
EXTRA_MODEL_SCAN_PATHS = [p for p in env("MODEL_SCAN_PATHS", "").split(":") if p]

WEB_TITLE = env("WEB_TITLE", "Llama Control Center")
DEFAULT_SERVER_HOST = env("DEFAULT_SERVER_HOST", "0.0.0.0")
DEFAULT_SERVER_PORT = int(env("DEFAULT_SERVER_PORT", "8081"))
DEFAULT_SERVER_ALIAS = env("DEFAULT_SERVER_ALIAS", "llama-local")
DEFAULT_CTX_SIZE = int(env("DEFAULT_CTX_SIZE", "4096"))
DEFAULT_THREADS = int(env("DEFAULT_THREADS", "4"))
DEFAULT_N_GPU_LAYERS = int(env("DEFAULT_N_GPU_LAYERS", "0"))
DEFAULT_PUBLIC_HOST = env("DEFAULT_PUBLIC_HOST", "")
DEFAULT_PUBLIC_PORT = int(env("DEFAULT_PUBLIC_PORT", str(DEFAULT_SERVER_PORT)))
