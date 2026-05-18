import os
from pathlib import Path

import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.config import DEFAULT_MODELS_DIR
from app.db import session_scope, engine
from app.main import app
from app.models import Model, Base
from app.runtime_settings import update_runtime_settings


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope='session', autouse=True)
def configure_binary():
    binary_dir = os.path.join(os.getcwd(), 'bin')
    os.makedirs(binary_dir, exist_ok=True)
    binary_path = os.path.join(binary_dir, 'llama-server')
    Path(binary_path).write_bytes(b'')
    Path(binary_path).chmod(0o755)
    update_runtime_settings(binary_path=binary_path)
    yield
    try:
        Path(binary_path).unlink()
    except FileNotFoundError:
        pass


@pytest.fixture
def mock_llama_server():
    with patch('app.llama_server_manager.start_llama_server') as mock:
        mock.return_value = True
        yield mock


@pytest.fixture
def mock_cleanup_process():
    with patch('app.llama_server_manager.cleanup_stale_process') as mock:
        yield mock


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def setup_models():
    local_path = os.path.join(DEFAULT_MODELS_DIR, 'test_model.gguf')
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, 'wb') as f:
        f.write(b'')

    with session_scope() as session:
        model = Model(
            name='Test Model',
            url='http://example.com/model.gguf',
            source_type='direct_url',
            local_path=local_path,
        )
        session.add(model)
        session.commit()
        return_id = model.id
    yield return_id


def test_start_llama_server(client, mock_llama_server, mock_cleanup_process, setup_models):
    response = client.post(
        '/server/start',
        data={'model_id': setup_models, 'apply_recommendation': 'true'},
        allow_redirects=False,
    )
    print('start response', response.status_code, response.json())
    assert response.status_code == 303
    mock_llama_server.assert_called_once()


def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert 'server_status' in response.json()


def test_cleanup_stale_process(client, mock_cleanup_process, setup_models):
    client.post('/server/start', data={'model_id': setup_models}, allow_redirects=False)
    response = client.post('/server/stop', allow_redirects=False)
    assert response.status_code == 303
    mock_cleanup_process.assert_called_once()
