from redis import Redis
from rq import Connection, Worker

from app.config import REDIS_URL


def main() -> None:
    redis_conn = Redis.from_url(REDIS_URL)
    with Connection(redis_conn):
        worker = Worker(["default"])
        worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
