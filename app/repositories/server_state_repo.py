from __future__ import annotations

from typing import Any

from app.db import session_scope
from app.models import ServerState


def load_state() -> dict[str, Any]:
    with session_scope() as s:
        row = s.get(ServerState, 1)
        if not row:
            return {}
        result: dict[str, Any] = {
            "pid": row.pid,
            "binary_path": row.binary_path,
            "model_path": row.model_path,
            "model_id": row.model_id,
            "host": row.host,
            "port": row.port,
            "alias": row.alias,
            "api_key": row.api_key,
            "ctx_size": row.ctx_size,
            "threads": row.threads,
            "n_gpu_layers": row.n_gpu_layers,
            "extra_args": row.extra_args,
            "started_at": row.started_at,
            "log_path": row.log_path,
            "status": row.status,
            "cmd": row.cmd,
        }
        return {k: v for k, v in result.items() if v is not None}


def save_state(state: dict[str, Any]) -> None:
    with session_scope() as s:
        row = s.get(ServerState, 1)
        if not row:
            row = ServerState(id=1)
            s.add(row)
        for key in (
            "pid",
            "binary_path",
            "model_path",
            "model_id",
            "host",
            "port",
            "alias",
            "api_key",
            "ctx_size",
            "threads",
            "n_gpu_layers",
            "extra_args",
            "started_at",
            "log_path",
            "status",
            "cmd",
        ):
            if key in state:
                setattr(row, key, state[key])


def clear_state() -> None:
    with session_scope() as s:
        row = s.get(ServerState, 1)
        if row:
            s.delete(row)
