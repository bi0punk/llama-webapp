from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from app.config import (
    DEFAULT_BINARY_CANDIDATES,
    DEFAULT_LLAMA_SEARCH_PATHS,
    DEFAULT_MODEL_SCAN_PATHS,
    EXTRA_LLAMA_SEARCH_PATHS,
    EXTRA_MODEL_SCAN_PATHS,
)
from app.runtime_settings import load_runtime_settings


EXECUTABLE_NAMES = ("llama-server", "llama-run", "llama-cli")


def _unique(seq: Iterable[str]) -> list[str]:
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


def model_scan_roots() -> list[str]:
    settings = load_runtime_settings()
    roots = [settings.model_root_dir] + DEFAULT_MODEL_SCAN_PATHS + EXTRA_MODEL_SCAN_PATHS
    return _unique([str(Path(p).expanduser()) for p in roots if p])


def scan_model_files(max_depth: int = 4) -> list[str]:
    results: list[str] = []
    for root in model_scan_roots():
        root_path = Path(root).expanduser()
        if not root_path.exists() or not root_path.is_dir():
            continue
        base_parts = len(root_path.parts)
        try:
            for current_root, dirs, files in os.walk(root_path):
                depth = len(Path(current_root).parts) - base_parts
                if depth >= max_depth:
                    dirs[:] = []
                for name in files:
                    if name.lower().endswith(".gguf"):
                        results.append(str((Path(current_root) / name).resolve()))
        except Exception:
            continue
    return sorted(_unique(results))
