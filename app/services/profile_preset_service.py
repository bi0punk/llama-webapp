from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.runtime_settings import RuntimeSettings, save_runtime_settings

PROFILES_PATH = Path(__file__).resolve().parent.parent / "data" / "server_profiles.json"


def load_presets() -> list[dict[str, Any]]:
    try:
        data = json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def apply_preset(preset_id: str, settings: RuntimeSettings | None = None) -> RuntimeSettings:
    presets = load_presets()
    for p in presets:
        if p["id"] == preset_id:
            if settings is None:
                from app.runtime_settings import load_runtime_settings

                settings = load_runtime_settings()
            for key, value in p["settings"].items():
                setattr(settings, key, value)
            save_runtime_settings(settings)
            return settings
    raise ValueError(f"Preset '{preset_id}' not found")
