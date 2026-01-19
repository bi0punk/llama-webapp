from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

from fastapi import Depends, FastAPI, Form, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from redis import Redis
from rq import Queue

from app.config import DATA_DIR, LLAMA_RUN_BIN, MODELS_DIR, REDIS_URL
from app.db import engine, session_scope
from app.models import Base, Job, Model
from app.tasks import download_model

app = FastAPI(title="Llama Web Model Hub")

# static + templates
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# redis queue
redis_conn = Redis.from_url(REDIS_URL)
queue = Queue("default", connection=redis_conn)


@app.on_event("startup")
def startup() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)


# --------- helpers ---------

def get_models_and_jobs() -> Dict[str, Any]:
    with session_scope() as s:
        models = s.query(Model).order_by(Model.created_at.desc()).all()
        jobs = s.query(Job).order_by(Job.created_at.desc()).limit(50).all()
        return {"models": models, "jobs": jobs}


def _ensure_llama_bin() -> None:
    if not Path(LLAMA_RUN_BIN).exists():
        raise HTTPException(
            status_code=500,
            detail=f"llama-run binary not found at {LLAMA_RUN_BIN}. Check your Docker build.",
        )


# --------- pages ---------

@app.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return RedirectResponse(url="/models")


@app.get("/models", response_class=HTMLResponse)
def models_page(request: Request):
    data = get_models_and_jobs()
    return templates.TemplateResponse(
        "models.html",
        {
            "request": request,
            "models": data["models"],
        },
    )


@app.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request):
    data = get_models_and_jobs()
    return templates.TemplateResponse(
        "jobs.html",
        {
            "request": request,
            "jobs": data["jobs"],
        },
    )


@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    data = get_models_and_jobs()
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "models": data["models"],
            "llama_run_bin": LLAMA_RUN_BIN,
        },
    )


# --------- partials for HTMX polling ---------

@app.get("/partials/models_table", response_class=HTMLResponse)
def models_table_partial(request: Request):
    with session_scope() as s:
        models = s.query(Model).order_by(Model.created_at.desc()).all()
        return templates.TemplateResponse(
            "partials/models_table.html",
            {"request": request, "models": models},
        )


@app.get("/partials/jobs_table", response_class=HTMLResponse)
def jobs_table_partial(request: Request):
    with session_scope() as s:
        jobs = s.query(Job).order_by(Job.created_at.desc()).limit(50).all()
        return templates.TemplateResponse(
            "partials/jobs_table.html",
            {"request": request, "jobs": jobs},
        )


@app.get("/jobs/{job_id}/log", response_class=PlainTextResponse)
def job_log(job_id: int):
    with session_scope() as s:
        job = s.get(Job, job_id)
        if not job or not job.log_path:
            return PlainTextResponse("No log available.")
        path = Path(job.log_path)
        if not path.exists():
            return PlainTextResponse("Log file not found.")
        # tail-ish
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()[-200:]
        return PlainTextResponse("\n".join(lines) + "\n")


# --------- actions ---------

@app.post("/models/add")
def add_model(
    name: str = Form(...),
    url: str = Form(...),
    source_type: str = Form("direct_url"),
):
    with session_scope() as s:
        m = Model(name=name.strip(), url=url.strip(), source_type=source_type.strip() or "direct_url")
        s.add(m)
    return RedirectResponse(url="/models", status_code=303)


@app.post("/models/import_registry")
def import_registry() -> RedirectResponse:
    # Import bundled registry entries (safe seed)
    registry_path = BASE_DIR / "model_registry.json"
    if not registry_path.exists():
        return RedirectResponse(url="/models", status_code=303)

    entries = json.loads(registry_path.read_text(encoding="utf-8"))
    with session_scope() as s:
        existing = {m.name for m in s.query(Model).all()}
        for e in entries:
            if e.get("name") in existing:
                continue
            s.add(Model(name=e["name"], url=e.get("url"), source_type=e.get("source_type", "direct_url")))
    return RedirectResponse(url="/models", status_code=303)


@app.post("/models/{model_id}/download")
def download(model_id: int):
    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        model.status = "DOWNLOADING"

        job = Job(type="download", status="queued", progress=0, message=f"Downloading model {model_id}")
        s.add(job)
        s.flush()
        job_id = job.id

    rq_job = queue.enqueue(download_model, job_id, model_id, job_timeout="12h")

    with session_scope() as s:
        job = s.get(Job, job_id)
        if job:
            job.rq_job_id = rq_job.id

    return RedirectResponse(url="/models", status_code=303)


@app.post("/models/{model_id}/delete")
def delete_model(model_id: int):
    with session_scope() as s:
        model = s.get(Model, model_id)
        if not model:
            return RedirectResponse(url="/models", status_code=303)

        # delete file on disk (best effort)
        if model.local_path:
            try:
                Path(model.local_path).unlink(missing_ok=True)
            except Exception:
                pass

        # delete directory
        try:
            model_dir = Path(MODELS_DIR) / f"model_{model.id}"
            if model_dir.exists():
                for p in model_dir.glob("*"):
                    try:
                        p.unlink()
                    except Exception:
                        pass
                try:
                    model_dir.rmdir()
                except Exception:
                    pass
        except Exception:
            pass

        s.delete(model)
    return RedirectResponse(url="/models", status_code=303)


# --------- websocket chat (stream llama-run output) ---------

@app.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            raw = await websocket.receive_text()
            payload = json.loads(raw)

            model_id = int(payload.get("model_id"))
            prompt = (payload.get("prompt") or "").strip()
            params: Dict[str, Any] = payload.get("params") or {}

            if not prompt:
                await websocket.send_text("[!] Prompt vacío\n")
                continue

            with session_scope() as s:
                model = s.get(Model, model_id)
                if not model or model.status != "READY" or not model.local_path:
                    await websocket.send_text("[!] Modelo no está READY o no existe en disco.\n")
                    continue
                model_path = model.local_path

            _ensure_llama_bin()

            threads = int(params.get("threads") or 6)
            temp = float(params.get("temp") or 0.8)
            ctx = int(params.get("ctx") or 2048)

            cmd = [
                LLAMA_RUN_BIN,
                model_path,
                "--threads",
                str(threads),
                "--temp",
                str(temp),
                "--context-size",
                str(ctx),
                prompt,
            ]

            await websocket.send_text(f"\n[cmd] {' '.join(cmd[:-1])} <PROMPT>\n\n")

            # Run llama-run as subprocess and stream stdout
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            assert proc.stdout is not None
            # stream bytes in chunks to keep UI responsive
            while True:
                chunk = await proc.stdout.read(512)
                if not chunk:
                    break
                try:
                    await websocket.send_text(chunk.decode("utf-8", errors="ignore"))
                except WebSocketDisconnect:
                    proc.kill()
                    raise

            rc = await proc.wait()
            await websocket.send_text(f"\n\n[done] exit_code={rc}\n")

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await websocket.send_text(f"\n[error] {e}\n")
        except Exception:
            pass
        return


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
