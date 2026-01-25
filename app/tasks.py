from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path

import requests

from app.config import HUGGING_FACE_TOKEN, LOGS_DIR, MODELS_DIR
from app.db import session_scope
from app.models import Model, Job


def _safe_filename(name: str) -> str:
    # basic hardening
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9._-]+", "_", name)
    return name[:200] or "model"


def _log(job: Job, line: str) -> None:
    if not job.log_path:
        return
    Path(job.log_path).parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().isoformat(timespec="seconds")
    with open(job.log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {line}\n")


def download_model(job_id: int, model_id: int) -> None:
    """Download a GGUF (or any file) from a direct URL.

    If HUGGING_FACE_TOKEN is set, it will be used as Bearer token.
    """
    os.makedirs(MODELS_DIR, exist_ok=True)
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

        # local model directory
        model_dir = os.path.join(MODELS_DIR, f"model_{model.id}")
        os.makedirs(model_dir, exist_ok=True)

        # derive filename
        guessed_name = model.name
        # if name doesn't end with gguf, allow any file, but keep safe
        filename = _safe_filename(guessed_name)
        local_path = os.path.join(model_dir, filename)

        headers = {}
        if HUGGING_FACE_TOKEN:
            headers["Authorization"] = f"Bearer {HUGGING_FACE_TOKEN}"

        _log(job, f"Starting download: {model.url}")
        _log(job, f"Saving to: {local_path}")

        try:
            with requests.get(model.url, headers=headers, stream=True, timeout=60) as r:
                # Common Hugging Face failure modes: gated/private repos (401/403)
                if r.status_code in (401, 403):
                    model.status = "NEEDS_TOKEN"
                    job.status = "error"
                    job.message = "Requiere HUGGING_FACE_TOKEN (HTTP %s)" % r.status_code
                    _log(job, f"ERROR: HTTP {r.status_code} (likely gated/private). Set HUGGING_FACE_TOKEN and retry.")
                    return
                if r.status_code == 429:
                    model.status = "ERROR"
                    job.status = "error"
                    job.message = "Rate limit (HTTP 429). Reintenta más tarde."
                    _log(job, "ERROR: HTTP 429 rate limited.")
                    return

                r.raise_for_status()
                total = int(r.headers.get("Content-Length", "0") or "0")

                downloaded = 0
                last_update = time.time()
                chunk_size = 1024 * 1024  # 1MB

                tmp_path = local_path + ".part"
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)

                        now = time.time()
                        if now - last_update >= 0.5:
                            if total > 0:
                                pct = int(downloaded * 100 / total)
                                job.progress = max(0, min(99, pct))
                            else:
                                # unknown total, show a rough progress bar
                                job.progress = min(99, job.progress + 1)
                            job.message = f"{downloaded/1024/1024:.1f} MB"
                            last_update = now

                os.replace(tmp_path, local_path)

            model.local_path = local_path
            model.size_bytes = os.path.getsize(local_path)
            model.status = "READY"

            job.progress = 100
            job.status = "done"
            job.message = "Download complete"
            _log(job, "Download complete")

        except Exception as e:
            model.status = "ERROR"
            job.status = "error"
            job.message = str(e)
            _log(job, f"ERROR: {e}")
            # keep partial file for debugging
            return
