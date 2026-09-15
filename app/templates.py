from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.auth import auth_enabled

BASE_DIR = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["auth_enabled"] = auth_enabled
