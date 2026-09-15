from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@patch("app.services.chat_service.get_server_status")
def test_chat_requires_running_server(mock_status, client):
    mock_status.return_value = {"status": "stopped", "state": {}}
    response = client.post("/api/playground/chat", json={"prompt": "hola"})
    assert response.status_code == 400


@patch("app.services.chat_service.get_server_status")
def test_chat_rejects_wrong_api_key(mock_status, client):
    mock_status.return_value = {"status": "running", "state": {"api_key": "sekret", "alias": "llama-local"}}
    response = client.post("/api/playground/chat", json={"prompt": "hola"}, headers={"X-Api-Key": "nope"})
    assert response.status_code == 401


@patch("httpx.AsyncClient")
@patch("app.services.chat_service.get_server_status")
def test_chat_proxies_response(mock_status, mock_client_cls, client):
    mock_status.return_value = {"status": "running", "state": {"api_key": "sekret", "alias": "llama-local"}}
    mock_http = MagicMock()
    mock_http.status_code = 200
    mock_http.json.return_value = {"choices": [{"message": {"content": "hola"}}]}
    mock_http.text = ""
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_http
    mock_client.__aenter__.return_value = mock_client
    mock_client_cls.return_value = mock_client

    response = client.post("/api/playground/chat", json={"prompt": "hola"}, headers={"X-Api-Key": "sekret"})
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "hola"
    _, kwargs = mock_client.post.call_args
    assert kwargs["json"]["model"] == "llama-local"
    assert kwargs["json"]["stream"] is False
