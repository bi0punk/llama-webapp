from __future__ import annotations

from typing import Any

import httpx

from app.config import HUGGING_FACE_TOKEN

HF_API = "https://huggingface.co/api"
HF_RESOLVE = "https://huggingface.co/{repo}/resolve/main/{path}"


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {HUGGING_FACE_TOKEN}"} if HUGGING_FACE_TOKEN else {}


def search_hf(query: str, limit: int = 10) -> list[dict[str, Any]]:
    try:
        response = httpx.get(
            f"{HF_API}/models",
            params={"search": query, "limit": limit},
            headers=_headers(),
            timeout=15.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, ValueError):
        return []

    results: list[dict[str, Any]] = []
    for item in response.json():
        results.append(
            {
                "id": item.get("id", ""),
                "downloads": item.get("downloads", 0),
                "likes": item.get("likes", 0),
                "tags": [t for t in item.get("tags", []) if isinstance(t, str)][:5],
            }
        )
    return results


def list_gguf_files(repo: str, recursive: bool = True) -> list[str]:
    try:
        response = httpx.get(
            f"{HF_API}/models/{repo}/tree/main",
            params={"recursive": "true" if recursive else "false"},
            headers=_headers(),
            timeout=15.0,
        )
        response.raise_for_status()
    except (httpx.HTTPError, ValueError):
        return []

    files: list[str] = []
    for item in response.json():
        path = item.get("path", "")
        if path.lower().endswith(".gguf"):
            files.append(path)
    files.sort()
    return files


def resolve_url(repo: str, path: str) -> str:
    return HF_RESOLVE.format(repo=repo, path=path)
