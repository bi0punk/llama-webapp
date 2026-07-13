from __future__ import annotations

from typing import Any

from redis import Redis
from rq import Queue

from app.config import REDIS_PASSWORD, REDIS_URL


def _redis_kwargs() -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if REDIS_PASSWORD:
        kwargs["password"] = REDIS_PASSWORD
    return kwargs


redis_conn = Redis.from_url(REDIS_URL, **_redis_kwargs())
queue = Queue("default", connection=redis_conn)
