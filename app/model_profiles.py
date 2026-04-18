from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from app.system_info import cpu_count

B_RE = re.compile(r"(?<!\d)(\d+(?:\.\d+)?)\s*[bB](?![a-zA-Z])")
Q_RE = re.compile(r"q([2-8])(?:[_-]?k(?:[_-]?([msl]))?)?", re.IGNORECASE)


def parse_billions(name: str) -> float | None:
    match = B_RE.search(name)
    if not match:
        return None
    try:
        return float(match.group(1))
    except Exception:
        return None


def parse_quant(name: str) -> str | None:
    match = Q_RE.search(name)
    if not match:
        return None
    q = match.group(1)
    suffix = match.group(2)
    return f"Q{q}{('-' + suffix.upper()) if suffix else ''}"


def guess_family(name: str) -> str:
    lowered = name.lower()
    for candidate in ["qwen", "llama", "mistral", "deepseek", "phi", "gemma", "codestral", "yi"]:
        if candidate in lowered:
            return candidate
    return "unknown"


def estimate_ram_gb(file_size_bytes: int | None) -> float | None:
    if not file_size_bytes:
        return None
    gb = file_size_bytes / (1024 ** 3)
    # rough memory budget for runtime + kv/cache overhead
    return round(max(gb * 1.35, gb + 1.2), 2)


def recommend_settings(model_name: str, file_size_bytes: int | None = None) -> dict[str, Any]:
    cpus = cpu_count()
    family = guess_family(model_name)
    billions = parse_billions(model_name)
    quant = parse_quant(model_name)
    est_ram = estimate_ram_gb(file_size_bytes)

    threads = cpus
    ctx_size = 4096
    extra_args = ["--parallel", "1", "--batch-size", "512", "--ubatch-size", "512"]
    n_gpu_layers = 0
    notes: list[str] = []

    if billions is not None:
        if billions <= 2:
            ctx_size = 8192
            notes.append("Modelo pequeño; se puede subir contexto sin castigar demasiado CPU/RAM.")
        elif billions <= 4:
            ctx_size = 8192
            extra_args = ["--parallel", "1", "--batch-size", "512", "--ubatch-size", "512"]
            notes.append("Modelo liviano; buen candidato para CPU-only y uso interactivo en LAN.")
        elif billions <= 8:
            ctx_size = 4096
            threads = max(2, min(cpus, cpus))
            extra_args = ["--parallel", "1", "--batch-size", "256", "--ubatch-size", "256"]
            notes.append("Rango medio; conviene mantener batch moderado para no disparar RAM.")
        elif billions <= 14:
            ctx_size = 4096
            threads = max(2, min(cpus, max(2, cpus - 1)))
            extra_args = ["--parallel", "1", "--batch-size", "128", "--ubatch-size", "128"]
            notes.append("Modelo pesado para CPU-only; usa batch más bajo y una sola conversación paralela.")
        else:
            ctx_size = 2048
            threads = max(2, min(cpus, max(2, cpus - 1)))
            extra_args = ["--parallel", "1", "--batch-size", "64", "--ubatch-size", "64"]
            notes.append("Modelo muy pesado; recomendado solo con bastante RAM o aceleración GPU.")

    if quant:
        notes.append(f"Cuantización detectada: {quant}.")

    if family in {"qwen", "codestral", "deepseek"}:
        notes.append("Familia orientada a código/instrucciones; útil para pruebas tipo chat y tareas técnicas.")

    if est_ram is not None:
        notes.append(f"RAM mínima orientativa estimada: ~{est_ram} GB para trabajar con cierto margen.")

    return {
        "family": family,
        "billions": billions,
        "quant": quant,
        "estimated_ram_gb": est_ram,
        "threads": threads,
        "ctx_size": ctx_size,
        "n_gpu_layers": n_gpu_layers,
        "extra_args": " ".join(extra_args),
        "notes": notes,
    }


def describe_model(path_or_name: str, file_size_bytes: int | None = None) -> dict[str, Any]:
    name = Path(path_or_name).name
    if file_size_bytes is None:
        try:
            file_size_bytes = Path(path_or_name).stat().st_size
        except Exception:
            file_size_bytes = None
    return recommend_settings(name, file_size_bytes)
