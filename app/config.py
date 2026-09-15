from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).resolve().parent.parent

# Las variables ya exportadas en el entorno prevalecen sobre las del archivo .env.
# pydantic-settings carga .env automáticamente y las variables de entorno tienen prioridad.


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_DIR / ".env"), extra="ignore")

    data_dir: str = str(PROJECT_DIR / "data")
    database_url: str = ""
    redis_url: str = "redis://127.0.0.1:6379/0"
    redis_password: str = ""
    hugging_face_token: str = ""
    web_token: str = ""
    default_models_dir: str = ""
    logs_dir: str = ""
    settings_path: str = ""
    server_state_path: str = ""
    llama_run_bin: str = "/opt/llama/bin/llama-run"
    llama_cli_bin: str = "/opt/llama/bin/llama-cli"
    llama_server_bin: str = "/opt/llama/bin/llama-server"
    llama_search_paths: str = ""
    model_scan_paths: str = ""
    web_title: str = "Llama Control Center"
    default_server_host: str = "127.0.0.1"
    default_server_port: int = 8081
    default_server_alias: str = "llama-local"
    default_ctx_size: int = 4096
    default_threads: int = 4
    default_n_gpu_layers: int = 0
    default_public_host: str = ""
    default_public_port: int = 8081
    sqlite_pool_size: int = 5
    sqlite_pool_timeout: int = 15
    sqlite_max_overflow: int = 10
    models_page_size: int = 100


_settings = Settings()

DATA_DIR = _settings.data_dir
DATABASE_URL = _settings.database_url or f"sqlite:///{DATA_DIR}/app.db"
REDIS_URL = _settings.redis_url
REDIS_PASSWORD = _settings.redis_password
HUGGING_FACE_TOKEN = _settings.hugging_face_token
WEB_TOKEN = _settings.web_token

DEFAULT_MODELS_DIR = _settings.default_models_dir or os.path.join(DATA_DIR, "models")
LOGS_DIR = _settings.logs_dir or os.path.join(DATA_DIR, "logs")
SETTINGS_PATH = _settings.settings_path or os.path.join(DATA_DIR, "runtime_settings.json")
SERVER_STATE_PATH = _settings.server_state_path or os.path.join(DATA_DIR, "llama_server_state.json")

LLAMA_RUN_BIN = _settings.llama_run_bin
LLAMA_CLI_BIN = _settings.llama_cli_bin
LLAMA_SERVER_BIN = _settings.llama_server_bin

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

EXTRA_LLAMA_SEARCH_PATHS = [p for p in _settings.llama_search_paths.split(":") if p]
EXTRA_MODEL_SCAN_PATHS = [p for p in _settings.model_scan_paths.split(":") if p]

WEB_TITLE = _settings.web_title
DEFAULT_SERVER_HOST = _settings.default_server_host
DEFAULT_SERVER_PORT = _settings.default_server_port
DEFAULT_SERVER_ALIAS = _settings.default_server_alias
DEFAULT_CTX_SIZE = _settings.default_ctx_size
DEFAULT_THREADS = _settings.default_threads
DEFAULT_N_GPU_LAYERS = _settings.default_n_gpu_layers
DEFAULT_PUBLIC_HOST = _settings.default_public_host
DEFAULT_PUBLIC_PORT = _settings.default_public_port

SQLITE_POOL_SIZE = _settings.sqlite_pool_size
SQLITE_POOL_TIMEOUT = _settings.sqlite_pool_timeout
SQLITE_MAX_OVERFLOW = _settings.sqlite_max_overflow

MODELS_PAGE_SIZE = _settings.models_page_size
