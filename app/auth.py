from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import quote

from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from app.config import WEB_TOKEN

COOKIE_NAME = "llama_session"
SESSION_MAX_AGE = 90 * 24 * 3600  # 90 días

_PUBLIC_PATHS = {"/login", "/logout", "/health"}

__all__ = [
    "auth_enabled",
    "create_session_token",
    "verify_web_token",
    "verify_session_token",
    "AuthMiddleware",
    "COOKIE_NAME",
    "SESSION_MAX_AGE",
    "WEB_TOKEN",
]


def auth_enabled() -> bool:
    return bool(WEB_TOKEN)


def _sign(value: str) -> str:
    return hmac.new(WEB_TOKEN.encode(), value.encode(), hashlib.sha256).hexdigest()


def create_session_token() -> str:
    ts = str(int(time.time()))
    return f"{ts}.{_sign(ts)}"


def verify_web_token(token: str) -> bool:
    if not auth_enabled():
        return False
    return hmac.compare_digest(token.strip(), WEB_TOKEN)


def verify_session_token(token: str | None) -> bool:
    if not auth_enabled() or not token:
        return False
    try:
        ts, sig = token.split(".", 1)
        if not hmac.compare_digest(sig, _sign(ts)):
            return False
        age = time.time() - int(ts)
        return 0 <= age <= SESSION_MAX_AGE
    except (ValueError, TypeError):
        return False


class AuthMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if not auth_enabled():
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in _PUBLIC_PATHS or path.startswith("/static/"):
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        if request.cookies.get(COOKIE_NAME) and verify_session_token(request.cookies.get(COOKIE_NAME)):
            await self.app(scope, receive, send)
            return

        response: JSONResponse | RedirectResponse
        if path.startswith("/api/") or path.startswith("/server/log"):
            response = JSONResponse({"detail": "Unauthorized"}, status_code=401)
        else:
            response = RedirectResponse(url=f"/login?next={quote(path, safe='')}", status_code=302)
        await response(scope, receive, send)
