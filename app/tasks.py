from __future__ import annotations

import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

from app.config import HUGGING_FACE_TOKEN, LOGS_DIR
from app.db import session_scope
from app.models import Job, Model
from app.runtime_settings import load_runtime_settings


FILENAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_filename(value: str) -> str:
    cleaned = FILENAME_RE.sub("_", value.strip())
    cleaned = cleaned.strip("._") or "model.gguf"
    if not cleaned.lower().endswith(".gguf"):
        cleaned += ".gguf"
    return cleaned


def _log(job: Job, message: str) -> None:
    if not job.log_path:
        return
    path = Path(job.log_path)
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")


def _download_target_path(model: Model) -> Path:
    settings = load_runtime_settings()
    root = Path(settings.model_root_dir).expanduser().resolve()
    os.makedirs(root, exist_ok=True)

    filename = _safe_filename(model.name)
    return root / filename


def _guess_filename_from_url(url: str) -> str:
    parsed = urlparse(url)
    name = Path(parsed.path).name or "model.gguf"
    return _safe_filename(name)


def download_model(job_id: int, model_id: int) -> None:
    """Download a GGUF file from a direct URL with basic validation."""
    os.makedirs(LOGS_DIR, exist_ok=True)

    with session_scope() as s:
        job = s.get(Job, job_id)
        model = s.get(Model, model_id)
        if job is None or model is None:
            return

        job.status = "running"
        job.progress = 0
        if not job.log_path:
            job.log_path = os.path.join(LOGS_DIR, f"job_{job_id}.log")

        if not model.url:
            model.status = "ERROR"
            job.status = "error"
            job.message = "Model has no URL"
            _log(job, "ERROR: model has no URL")
            return

        local_path = _download_target_path(model)
        if local_path.exists() and local_path.is_dir():
            model.status = "ERROR"
            job.status = "error"
            job.message = f"Ruta destino inválida: {local_path}"
            _log(job, f"ERROR: invalid destination path {local_path}")
            return

        if not model.name.lower().endswith(".gguf"):
            filename = _guess_filename_from_url(model.url)
            model.name = filename
            local_path = _download_target_path(model)

        tmp_path = local_path.with_suffix(local_path.suffix + ".part")

        headers = {}
        if HUGGING_FACE_TOKEN:
            headers["Authorization"] = f"Bearer {HUGGING_FACE_TOKEN}"

        _log(job, f"Starting download: {model.url}")
        _log(job, f"Saving to: {local_path}")
        if HUGGING_FACE_TOKEN:
            _log(job, "Auth: Bearer token present")
        else:
            _log(job, "Auth: NO token (public only)")

        try:
            with requests.Session() as sess:
                try:
                    head = sess.head(model.url, headers=headers, allow_redirects=True, timeout=30)
                    _log(job, f"HEAD status={head.status_code} final_url={head.url}")
                except Exception as exc:
                    _log(job, f"WARN: HEAD failed: {exc}")

                with sess.get(model.url, headers=headers, stream=True, allow_redirects=True, timeout=60) as response:
                    _log(job, f"GET status={response.status_code} final_url={response.url}")

                    if response.status_code in (401, 403):
                        model.status = "NEEDS_TOKEN"
                        job.status = "error"
                        job.message = f"Requiere HUGGING_FACE_TOKEN (HTTP {response.status_code})"
                        _log(job, f"ERROR: HTTP {response.status_code} gated/private model")
                        return
                    if response.status_code == 429:
                        model.status = "ERROR"
                        job.status = "error"
                        job.message = "Rate limit (HTTP 429). Reintenta más tarde."
                        _log(job, "ERROR: HTTP 429 rate limited")
                        return

                    response.raise_for_status()
                    content_type = (response.headers.get("Content-Type") or "").lower()
                    if "text/html" in content_type:
                        model.status = "NEEDS_TOKEN" if not HUGGING_FACE_TOKEN else "ERROR"
                        job.status = "error"
                        job.message = f"Descarga devolvió HTML ({content_type})."
                        _log(job, f"ERROR: got HTML instead of GGUF. content-type={content_type}")
                        return

                    total = int(response.headers.get("Content-Length", "0") or "0")
                    downloaded = 0
                    last_update = time.time()

                    with open(tmp_path, "wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if not chunk:
                                continue
                            handle.write(chunk)
                            downloaded += len(chunk)

                            now = time.time()
                            if now - last_update >= 0.5:
                                if total > 0:
                                    pct = int(downloaded * 100 / total)
                                    job.progress = max(0, min(99, pct))
                                else:
                                    job.progress = min(99, job.progress + 1)
                                job.message = f"{downloaded / 1024 / 1024:.1f} MB"
                                last_update = now

            with open(tmp_path, "rb") as handle:
                magic = handle.read(4)
                head = handle.read(64)

            if magic != b"GGUF":
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
                model.status = "ERROR"
                job.status = "error"
                job.message = f"Archivo descargado no es GGUF (magic={magic!r})"
                _log(job, f"ERROR: not GGUF. magic={magic!r} head={head[:20]!r}")
                return

            os.replace(tmp_path, local_path)

            model.local_path = str(local_path)
            model.size_bytes = os.path.getsize(local_path)
            model.status = "READY"

            job.progress = 100
            job.status = "done"
            job.message = "Download complete"
            _log(job, "Download complete")
        except Exception as exc:
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except Exception:
                pass
            model.status = "ERROR"
            job.status = "error"
            job.message = str(exc)
            _log(job, f"ERROR: {exc}")
