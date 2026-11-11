"""Tests del worker RQ sin Redis real."""

from unittest.mock import MagicMock, patch

import worker


def test_main_configura_redis_y_arranca_worker(monkeypatch):
    monkeypatch.setattr(worker, "REDIS_URL", "redis://example:6379/0")
    monkeypatch.setattr(worker, "REDIS_PASSWORD", "secreto")

    with patch.object(worker, "Redis") as redis_cls, patch.object(worker, "Worker") as worker_cls:
        conn = MagicMock()
        redis_cls.from_url.return_value = conn
        rq_worker = MagicMock()
        worker_cls.return_value = rq_worker

        worker.main()

        redis_cls.from_url.assert_called_once_with("redis://example:6379/0", password="secreto")
        worker_cls.assert_called_once_with(["default"], connection=conn)
        rq_worker.work.assert_called_once_with(with_scheduler=False)


def test_main_sin_password_no_pasa_kwargs(monkeypatch):
    monkeypatch.setattr(worker, "REDIS_URL", "redis://example:6379/0")
    monkeypatch.setattr(worker, "REDIS_PASSWORD", "")

    with patch.object(worker, "Redis") as redis_cls, patch.object(worker, "Worker") as worker_cls:
        worker.main()
        redis_cls.from_url.assert_called_once_with("redis://example:6379/0")
        worker_cls.return_value.work.assert_called_once_with(with_scheduler=False)
