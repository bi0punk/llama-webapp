from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.db import engine
from app.main import app
from app.models import Base
from app.services.huggingface_service import list_gguf_files, resolve_url, search_hf


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@patch("app.services.huggingface_service.httpx.get")
def test_search_hf_parses_results(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = lambda: None
    mock_get.return_value.json.return_value = [
        {"id": "org/model", "downloads": 1200, "likes": 34, "tags": ["llama", "gguf"]}
    ]
    results = search_hf("llama", limit=5)
    assert results == [
        {"id": "org/model", "downloads": 1200, "likes": 34, "tags": ["llama", "gguf"]}
    ]
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["search"] == "llama"
    assert kwargs["params"]["limit"] == 5


@patch("app.services.huggingface_service.httpx.get")
def test_search_hf_returns_empty_on_error(mock_get):
    from httpx import HTTPError

    mock_get.side_effect = HTTPError("boom")
    assert search_hf("llama") == []


@patch("app.services.huggingface_service.httpx.get")
def test_list_gguf_files_filters(mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status = lambda: None
    mock_get.return_value.json.return_value = [
        {"path": "model-q4_k_m.gguf"},
        {"path": "README.md"},
        {"path": "nested/tiny.gguf"},
    ]
    files = list_gguf_files("org/model")
    assert files == ["model-q4_k_m.gguf", "nested/tiny.gguf"]


def test_resolve_url():
    assert resolve_url("org/model", "x.gguf") == "https://huggingface.co/org/model/resolve/main/x.gguf"


@patch("app.services.huggingface_service.search_hf")
def test_hf_search_endpoint(mock_search, client):
    mock_search.return_value = [{"id": "org/model", "downloads": 1, "likes": 0, "tags": []}]
    response = client.get("/api/hf/search", params={"q": "llama"})
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == "org/model"


@patch("app.services.huggingface_service.list_gguf_files")
def test_hf_files_endpoint(mock_files, client):
    mock_files.return_value = ["a.gguf", "b.gguf"]
    response = client.get("/api/hf/files", params={"repo": "org/model"})
    assert response.status_code == 200
    assert response.json()["files"] == ["a.gguf", "b.gguf"]
