"""Smoke tests: validan migración RQ en worker y render de partials (firma TemplateResponse)."""

import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base


def test_worker_import_uses_modern_rq_api():
    """worker.py debe importar y exponer main() sin usar rq.Connection (removido en RQ moderno)."""
    import worker

    assert callable(worker.main)
    import inspect

    src = inspect.getsource(worker)
    assert "Connection" not in src, "worker.py aún referencia rq.Connection (API removido)"
    assert "Worker(" in src


def setup_function():
    Base.metadata.create_all(bind=engine)


def teardown_function():
    Base.metadata.drop_all(bind=engine)


def test_partials_render_and_curl_examples(client):
    """Los endpoints de partials deben renderizar HTML (ejercita la nueva firma TemplateResponse)."""
    for path in ("/partials/jobs_table", "/partials/models_table"):
        r = client.get(path)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
        assert "text/html" in r.headers.get("content-type", "")
        assert len(r.text) > 0

    r = client.get("/api/curl_examples")
    assert r.status_code == 200
    payload = r.json()
    assert isinstance(payload, dict)


def test_system_discovery_endpoint(client):
    r = client.get("/api/system/discovery")
    assert r.status_code == 200
    data = r.json()
    for key in ("binaries", "scan_roots", "models_found", "system"):
        assert key in data


@pytest.fixture
def client():
    return TestClient(app)
