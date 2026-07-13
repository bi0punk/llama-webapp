from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from app.config import (
    DEFAULT_BINARY_CANDIDATES,
    DEFAULT_LLAMA_SEARCH_PATHS,
    EXTRA_LLAMA_SEARCH_PATHS,
)
from app.runtime_settings import load_runtime_settings

EXECUTABLE_NAMES = ("llama-server", "llama-run", "llama-cli")


def _unique(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if not item:
            continue
        if item not in seen:
            out.append(item)
            seen.add(item)
    return out


def candidate_binary_paths() -> list[str]:
    settings = load_runtime_settings()
    paths: list[str] = []
    if settings.binary_path:
        paths.append(settings.binary_path)

    for name in EXECUTABLE_NAMES:
        discovered = shutil.which(name)
        if discovered:
            paths.append(discovered)

    for candidate in DEFAULT_BINARY_CANDIDATES:
        paths.append(candidate)

    search_roots = _unique(DEFAULT_LLAMA_SEARCH_PATHS + EXTRA_LLAMA_SEARCH_PATHS)
    for root in search_roots:
        path = Path(root)
        if not path.exists() or not path.is_dir():
            continue
        try:
            for entry in path.iterdir():
                if entry.name in EXECUTABLE_NAMES and os.access(entry, os.X_OK):
                    paths.append(str(entry.resolve()))
        except Exception:
            continue

    return _unique(paths)


def detect_binary_version(binary_path: str) -> str:
    try:
        result = subprocess.run(
            [binary_path, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
            check=False,
        )
        line = (result.stdout or "").strip().splitlines()
        if line:
            return line[0][:240]
    except Exception:
        pass
    return "desconocida"


def find_llama_server() -> dict[str, str | bool] | None:
    path = shutil.which("llama-server")
    if not path:
        return None
    version = detect_binary_version(path)
    return {"path": path, "exists": True, "name": "llama-server", "version": version}


def find_llama_binaries() -> list[dict[str, str | bool]]:
    results: list[dict[str, str | bool]] = []
    for path in candidate_binary_paths():
        exists = Path(path).exists()
        results.append(
            {
                "path": path,
                "exists": exists,
                "name": Path(path).name,
                "version": detect_binary_version(path) if exists else "no encontrado",
            }
        )
    return results
