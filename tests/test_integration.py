from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

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
def configure_binary(tmp_path_factory: pytest.TempPathFactory):
    binary_dir = tmp_path_factory.mktemp("bin")
    binary_path = binary_dir / "llama-server"
    binary_path.write_bytes(b"")
    binary_path.chmod(0o755)
    update_runtime_settings(binary_path=str(binary_path))
    yield


@pytest.fixture
def mock_llama_server():
    with patch("app.routes.actions.start_llama_server") as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_cleanup_process():
    with patch("app.main.cleanup_stale_process") as mock:
        yield mock


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def setup_models(tmp_path: Path):
    models_dir = tmp_path / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    local_path = models_dir / "test_model.gguf"
    local_path.write_bytes(b"")

    update_runtime_settings(model_root_dir=str(models_dir))

    with session_scope() as session:
        model = Model(
            name="Test Model",
            url="http://example.com/model.gguf",
            source_type="direct_url",
            local_path=str(local_path),
        )
        session.add(model)
        session.commit()
        return_id = model.id
    yield return_id


def test_start_llama_server(client, mock_llama_server, setup_models):
    response = client.post(
        "/server/start",
        data={"model_id": setup_models, "apply_recommendation": "true"},
        follow_redirects=False,
    )
    print("start response", response.status_code)
    assert response.status_code == 303
    mock_llama_server.assert_called_once()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert "server_status" in response.json()


def test_cleanup_stale_process(client, mock_llama_server, mock_cleanup_process, setup_models):
    # El lifespan (startup) se ejecuta al entrar en el context manager,
    # momento en el que cleanup_stale_process ya está parcheado.
    with client:
        client.post("/server/start", data={"model_id": setup_models}, follow_redirects=False)
        response = client.post("/server/stop", follow_redirects=False)
        assert response.status_code == 303
    mock_cleanup_process.assert_called_once()
