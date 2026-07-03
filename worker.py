from typing import Any

from redis import Redis
from rq import Worker

from app.config import REDIS_PASSWORD, REDIS_URL


def main() -> None:
    kwargs: dict[str, Any] = {}
    if REDIS_PASSWORD:
        kwargs["password"] = REDIS_PASSWORD
    redis_conn = Redis.from_url(REDIS_URL, **kwargs)
    worker = Worker(["default"], connection=redis_conn)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
