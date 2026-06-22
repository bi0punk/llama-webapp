from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import DATA_DIR, LOGS_DIR, WEB_TITLE
from app.db import engine
from app.deps import BASE_DIR
from app.discovery import find_llama_server
from app.llama_server_manager import cleanup_stale_process
from app.models import Base
from app.routes import actions, api, web
from app.runtime_settings import load_runtime_settings, save_runtime_settings
from app.system_info import default_public_host


class _CachedStaticFiles(StaticFiles):
    def file_response(self, *args: Any, **kwargs: Any) -> Any:
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "public, max-age=3600, immutable"
        return resp


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    cleanup_stale_process()

    settings = load_runtime_settings()
    if not settings.public_host:
        settings.public_host = default_public_host()

    llama_server = find_llama_server()
    if llama_server and (not settings.binary_path or not Path(settings.binary_path).expanduser().exists()):
        settings.binary_path = str(llama_server["path"])

    save_runtime_settings(settings)
    yield


app = FastAPI(title=WEB_TITLE, lifespan=lifespan)

app.mount(
    "/static",
    _CachedStaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

app.include_router(web.router)
app.include_router(api.router)
app.include_router(actions.router)


if __name__ == "__main__":
    import uvicorn

    web_host = os.getenv("WEB_HOST", "127.0.0.1")
    web_port = int(os.getenv("WEB_PORT", "8000"))
    uvicorn.run("app.main:app", host=web_host, port=web_port, reload=False)
