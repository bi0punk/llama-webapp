import asyncio
import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base
from app.routes.api import _stream_log_changes


def _event_text(event: str) -> str:
    payload = event.split("data: ", 1)[1].strip()
    return json.loads(payload)["text"]


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_metrics_endpoint_when_stopped(client):
    response = client.get("/api/server/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False


def test_metrics_endpoint_reflects_mocked_metrics(client):
    fake = {
        "running": True,
        "pid": 42,
        "process": {"cpu_percent": 12.5, "rss_bytes": 1024, "cpu_seconds": 3.0},
        "llama": {"slots_idle": 1, "slots_processing": 0},
    }
    with patch("app.llama_server_manager.get_server_metrics", return_value=fake):
        response = client.get("/api/server/metrics")
        assert response.status_code == 200
        assert response.json() == fake


def test_log_stream_emits_initial_tail(tmp_path):
    log_path = tmp_path / "llama_server.log"
    log_path.write_text("primera línea\nsegunda línea\n", encoding="utf-8")

    async def collect() -> str:
        gen = _stream_log_changes(log_path, log_path.read_text(encoding="utf-8"), poll_interval=0.01)
        try:
            return await anext(gen)
        finally:
            await gen.aclose()

    event = asyncio.run(collect())
    assert "primera línea" in _event_text(event)
    assert "segunda línea" in _event_text(event)


def test_log_stream_emits_delta(tmp_path):
    log_path = tmp_path / "llama_server.log"
    log_path.write_text("inicio\n", encoding="utf-8")
    initial = log_path.read_text(encoding="utf-8")

    async def collect() -> tuple[str, str]:
        gen = _stream_log_changes(log_path, initial, poll_interval=0.01)
        try:
            first = await anext(gen)
            log_path.write_text("inicio\nnueva línea\n", encoding="utf-8")
            second = await anext(gen)
            return first, second
        finally:
            await gen.aclose()

    first, second = asyncio.run(collect())
    assert "inicio" in _event_text(first)
    assert "nueva línea" in _event_text(second)
