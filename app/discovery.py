from __future__ import annotations

import os
from pathlib import Path

from app.config import DEFAULT_MODEL_SCAN_PATHS, EXTRA_MODEL_SCAN_PATHS
from app.runtime_settings import load_runtime_settings


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
