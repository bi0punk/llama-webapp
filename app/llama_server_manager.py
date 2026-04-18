from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from app.config import LOGS_DIR, SERVER_STATE_PATH
from app.runtime_settings import RuntimeSettings


def _state_path() -> Path:
    return Path(SERVER_STATE_PATH)


def load_server_state() -> dict[str, Any]:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_server_state(state: dict[str, Any]) -> None:
    path = _state_path()
    os.makedirs(path.parent, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_server_state() -> None:
    path = _state_path()
    if path.exists():
        path.unlink()


def is_pid_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _log_path() -> Path:
    os.makedirs(LOGS_DIR, exist_ok=True)
    return Path(LOGS_DIR) / "llama_server.log"


def server_log_tail(lines: int = 150) -> str:
    path = _log_path()
    if not path.exists():
        return "No hay log todavía."
    content = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(content[-lines:]) + "\n"


def server_http_status(state: dict[str, Any]) -> dict[str, Any]:
    port = int(state.get("port") or 0)
    api_key = state.get("api_key") or ""
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    base_url = f"http://127.0.0.1:{port}"

    for endpoint in ("/health", "/v1/models"):
        try:
            response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=1.5)
            return {
                "reachable": True,
                "http_status": response.status_code,
                "endpoint": endpoint,
                "ok": response.ok,
            }
        except Exception:
            continue

    return {
        "reachable": False,
        "http_status": None,
        "endpoint": None,
        "ok": False,
    }


def get_server_status() -> dict[str, Any]:
    state = load_server_state()
    pid = state.get("pid")
    running = is_pid_running(pid)
    http_info = server_http_status(state) if running and state.get("port") else {"reachable": False, "ok": False}

    status = "stopped"
    if running and http_info.get("reachable"):
        status = "running"
    elif running:
        status = "starting"

    if state and not running:
        status = "stopped"

    return {
        "status": status,
        "pid": pid,
        "state": state,
        "http": http_info,
        "log_path": str(_log_path()),
    }


def build_server_command(
    binary_path: str,
    model_path: str,
    settings: RuntimeSettings,
) -> list[str]:
    cmd = [
        binary_path,
        "-m",
        model_path,
        "--host",
        settings.server_host,
        "--port",
        str(settings.server_port),
        "--alias",
        settings.alias,
        "--ctx-size",
        str(settings.ctx_size),
        "--threads",
        str(settings.threads),
    ]

    if settings.n_gpu_layers and int(settings.n_gpu_layers) > 0:
        cmd.extend(["-ngl", str(settings.n_gpu_layers)])
    if settings.api_key:
        cmd.extend(["--api-key", settings.api_key])
    if settings.extra_args:
        cmd.extend(shlex.split(settings.extra_args))
    return cmd


def start_llama_server(binary_path: str, model_path: str, settings: RuntimeSettings, model_id: int | None = None) -> dict[str, Any]:
    current = get_server_status()
    if current["status"] in {"running", "starting"}:
        raise RuntimeError("Ya existe un llama-server activo o iniciando. Deténlo antes de iniciar otro.")

    log_path = _log_path()
    os.makedirs(log_path.parent, exist_ok=True)
    cmd = build_server_command(binary_path, model_path, settings)

    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(f"\n=== {datetime.utcnow().isoformat()}Z starting llama-server ===\n")
        handle.write("CMD: " + " ".join(cmd) + "\n")
        handle.flush()
        process = subprocess.Popen(
            cmd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    time.sleep(0.7)
    if process.poll() is not None:
        raise RuntimeError(
            "llama-server terminó inmediatamente. Revisa el log para ver el error real.\n\n"
            + server_log_tail(lines=80)
        )

    state = {
        "pid": process.pid,
        "binary_path": binary_path,
        "model_path": model_path,
        "model_id": model_id,
        "host": settings.server_host,
        "port": settings.server_port,
        "alias": settings.alias,
        "api_key": settings.api_key,
        "ctx_size": settings.ctx_size,
        "threads": settings.threads,
        "n_gpu_layers": settings.n_gpu_layers,
        "extra_args": settings.extra_args,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "cmd": cmd,
        "log_path": str(log_path),
    }
    save_server_state(state)
    return state


def stop_llama_server() -> dict[str, Any]:
    state = load_server_state()
    pid = state.get("pid")
    if not pid or not is_pid_running(pid):
        clear_server_state()
        return {"stopped": False, "message": "No había un llama-server activo."}

    try:
        os.killpg(pid, signal.SIGTERM)
    except Exception:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as exc:
            return {"stopped": False, "message": f"No se pudo detener el proceso: {exc}"}

    for _ in range(20):
        if not is_pid_running(pid):
            clear_server_state()
            return {"stopped": True, "message": "llama-server detenido correctamente."}
        time.sleep(0.25)

    try:
        os.killpg(pid, signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception as exc:
            return {"stopped": False, "message": f"No se pudo forzar cierre del proceso: {exc}"}

    clear_server_state()
    return {"stopped": True, "message": "llama-server detenido con SIGKILL."}
