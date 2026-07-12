from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_MODELS_DIR
from app.db import engine, session_scope
from app.main import app
from app.models import Base, Model
from app.runtime_settings import update_runtime_settings


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def configure_binary(tmp_path_factory: pytest.TempPathFactory) -> None:
    tmp_dir = tmp_path_factory.mktemp("bin")
    binary_path = tmp_dir / "llama-server"
    binary_path.write_bytes(b"")
    binary_path.chmod(0o755)
    update_runtime_settings(binary_path=str(binary_path))
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def setup_model():
    local_path = os.path.join(DEFAULT_MODELS_DIR, "route_test_model.gguf")
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    Path(local_path).write_bytes(b"")

    with session_scope() as session:
        model = Model(
            name="Route Test",
            url="http://example.com/route.gguf",
            source_type="direct_url",
            local_path=local_path,
        )
        session.add(model)
        session.commit()
        return model.id


# ── Health ───────────────────────────────────────────────────────────


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "server_status" in data
    assert "db_ok" in data


# ── Server status API ────────────────────────────────────────────────


def test_api_server_status(client):
    resp = client.get("/api/server/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "loopback_base_url" in data
    assert "advertised_base_url" in data


def test_api_server_log_tail(client):
    resp = client.get("/api/server/log_tail")
    assert resp.status_code == 200
    data = resp.json()
    assert "tail" in data


# ── System discovery ─────────────────────────────────────────────────


def test_api_system_discovery(client):
    resp = client.get("/api/system/discovery")
    assert resp.status_code == 200
    data = resp.json()
    assert "binaries" in data
    assert "scan_roots" in data
    assert "models_found" in data
    assert "system" in data


# ── Curl examples ────────────────────────────────────────────────────


def test_api_curl_examples(client):
    resp = client.get("/api/curl_examples")
    assert resp.status_code == 200
    data = resp.json()
    assert "localhost" in data
    assert "lan" in data


# ── Models API ───────────────────────────────────────────────────────


def test_api_model_profile(client, setup_model):
    resp = client.get(f"/api/models/{setup_model}/profile")
    assert resp.status_code == 200
    data = resp.json()
    assert data["model_id"] == setup_model
    assert "profile" in data


def test_api_model_profile_not_found(client):
    resp = client.get("/api/models/99999/profile")
    assert resp.status_code == 404


# ── Partials ─────────────────────────────────────────────────────────


def test_jobs_table_partial(client):
    resp = client.get("/partials/jobs_table")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_models_table_partial(client):
    resp = client.get("/partials/models_table")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


# ── Web pages ────────────────────────────────────────────────────────


def test_server_page(client):
    resp = client.get("/server")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")


def test_models_page(client):
    resp = client.get("/models")
    assert resp.status_code == 200


def test_jobs_page(client):
    resp = client.get("/jobs")
    assert resp.status_code == 200


def test_playground_page(client):
    resp = client.get("/playground")
    assert resp.status_code == 200


def test_root_redirects(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/server"


# ── Server actions ───────────────────────────────────────────────────


@patch("app.routes.actions.start_llama_server")
def test_server_start(mock_start, client, setup_model):
    resp = client.post("/server/start", data={"model_id": setup_model}, follow_redirects=False)
    assert resp.status_code == 303


@patch("app.routes.actions.stop_llama_server")
def test_server_stop(mock_stop, client):
    resp = client.post("/server/stop", follow_redirects=False)
    assert resp.status_code == 303


# ── Model actions ────────────────────────────────────────────────────


def test_scan_local_models(client):
    resp = client.post("/models/scan_local", follow_redirects=False)
    assert resp.status_code == 303


def test_add_model(client):
    data = {"name": "New Model", "url": "http://example.com/new.gguf"}
    resp = client.post("/models/add", data=data, follow_redirects=False)
    assert resp.status_code == 303


@patch("app.deps.queue.enqueue")
def test_add_and_download(mock_enqueue, client):
    mock_job = MagicMock()
    mock_job.id = "test_rq_job_123"
    mock_enqueue.return_value = mock_job
    resp = client.post(
        "/models/add_and_download",
        data={"name": "Download Test", "url": "http://example.com/dl.gguf"},
        follow_redirects=False,
    )
    assert resp.status_code == 303
    mock_enqueue.assert_called_once()


def test_delete_model(client, setup_model):
    resp = client.post(f"/models/{setup_model}/delete", follow_redirects=False)
    assert resp.status_code == 303


# ── Settings actions ─────────────────────────────────────────────────


def test_save_settings(client):
    resp = client.post(
        "/settings/save",
        data={
            "binary_path": "/usr/bin/llama-server",
            "model_root_dir": "/tmp/models",
            "server_host": "0.0.0.0",
            "server_port": 8081,
            "public_host": "",
            "public_port": 8081,
            "alias": "test-ai",
            "ctx_size": 4096,
            "threads": 4,
            "n_gpu_layers": 0,
            "api_key": "",
            "extra_args": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303


def test_apply_model_profile(client, setup_model):
    resp = client.post("/settings/apply_model_profile", data={"model_id": setup_model}, follow_redirects=False)
    assert resp.status_code == 303
