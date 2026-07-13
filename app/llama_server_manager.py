from __future__ import annotations

import json
import os
import re
import shlex
import signal
import subprocess
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from app.config import LOGS_DIR
from app.repositories.server_state_repo import clear_state, load_state, save_state
from app.runtime_settings import RuntimeSettings

# Flags válidos: letras, dígitos, guiones y puntos (con al menos un alnum).
_ALLOWED_ARG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _migrate_from_json() -> dict[str, Any]:
    from app.config import SERVER_STATE_PATH

    path = Path(SERVER_STATE_PATH)
    if not path.exists():
        return {}
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        save_state(data)
        path.unlink(missing_ok=True)
        return data
    except Exception:
        return {}


def load_server_state() -> dict[str, Any]:
    state = load_state()
    if not state:
        state = _migrate_from_json()
    return state


def save_server_state(state: dict[str, Any]) -> None:
    save_state(state)


def clear_server_state() -> None:
    clear_state()


def is_pid_running(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_process_group(pid: int, sig: int = signal.SIGTERM) -> None:
    with suppress(ProcessLookupError):
        os.killpg(pid, sig)
    with suppress(ProcessLookupError):
        os.kill(pid, sig)


def cleanup_stale_process() -> None:
    state = load_server_state()
    pid = state.get("pid")
    if pid and is_pid_running(pid):
        kill_process_group(pid, signal.SIGTERM)
        for _ in range(10):
            if not is_pid_running(pid):
                break
            time.sleep(0.2)
        else:
            kill_process_group(pid, signal.SIGKILL)
    clear_server_state()


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

    endpoints = ["/health", "/v1/models"]
    for attempt in range(3):
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", headers=headers, timeout=2.0)
                return {
                    "reachable": True,
                    "http_status": response.status_code,
                    "endpoint": endpoint,
                    "ok": response.ok,
                }
            except Exception:
                continue
        if attempt < 2:
            time.sleep(0.5)

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
        for arg in shlex.split(settings.extra_args):
            if arg.startswith("-"):
                key = arg.split("=")[0]
                if not _ALLOWED_ARG_RE.match(key.lstrip("-")):
                    raise ValueError(f"Argumento no permitido: {arg}")
            cmd.append(arg)
    return cmd


def start_llama_server(
    binary_path: str,
    model_path: str,
    settings: RuntimeSettings,
    model_id: int | None = None,
) -> dict[str, Any]:
    current = get_server_status()
    if current["status"] in {"running", "starting"}:
        raise RuntimeError("Ya existe un llama-server activo o iniciando. Deténlo antes de iniciar otro.")

    log_path = _log_path()
    os.makedirs(log_path.parent, exist_ok=True)
    cmd = build_server_command(binary_path, model_path, settings)

    with open(log_path, "a", encoding="utf-8") as handle:
        handle.write(f"\n=== {datetime.now(UTC).isoformat()}Z starting llama-server ===\n")
        handle.write("CMD: " + " ".join(cmd) + "\n")
        handle.flush()
        process = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)

    for _ in range(10):
        if process.poll() is not None:
            raise RuntimeError(
                "llama-server terminó inmediatamente. Revisa el log para ver el error real.\n\n"
                + server_log_tail(lines=80)
            )
        if process.pid is not None and is_pid_running(process.pid):
            break
        time.sleep(0.2)
    else:
        raise RuntimeError("llama-server no arrancó después de 2s.")

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
        "started_at": datetime.now(UTC).isoformat() + "Z",
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

    kill_process_group(pid, signal.SIGTERM)

    for _ in range(40):
        if not is_pid_running(pid):
            clear_server_state()
            return {"stopped": True, "message": "llama-server detenido correctamente."}
        time.sleep(0.25)

    kill_process_group(pid, signal.SIGKILL)
    clear_server_state()
    return {"stopped": True, "message": "llama-server detenido con SIGKILL (timeout 10s)."}
