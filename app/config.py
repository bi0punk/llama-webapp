import os


def env(key: str, default: str | None = None) -> str:
    val = os.getenv(key)
    if val is None or val == "":
        if default is None:
            return ""
        return default
    return val


DATA_DIR = env("DATA_DIR", "/data")
DATABASE_URL = env("DATABASE_URL", f"sqlite:///{DATA_DIR}/app.db")
REDIS_URL = env("REDIS_URL", "redis://redis:6379/0")
HUGGING_FACE_TOKEN = env("HUGGING_FACE_TOKEN", "")
LLAMA_RUN_BIN = env("LLAMA_RUN_BIN", "/usr/local/bin/llama-run")

# Where downloaded models live
MODELS_DIR = os.path.join(DATA_DIR, "models")
LOGS_DIR = os.path.join(DATA_DIR, "logs")
