from __future__ import annotations

import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent


def load_registry() -> list[dict[str, Any]]:
    registry_path = BASE_DIR / "model_registry.json"
    if not registry_path.exists():
        return []
    try:
        entries = json.loads(registry_path.read_text(encoding="utf-8"))
        return entries if isinstance(entries, list) else []
    except Exception:
        return []
