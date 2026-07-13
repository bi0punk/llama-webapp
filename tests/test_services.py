from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.models import Model
from app.runtime_settings import RuntimeSettings
from app.services.curl_service import build_curl_examples
from app.services.model_service import enqueue_download, import_local_models
from app.services.profile_service import get_model_profile, precompute_profiles
from app.services.url_service import advertised_base_url, loopback_base_url

# ── url_service ───────────────────────────────────────────────────────


def test_loopback_base_url() -> None:
    settings = RuntimeSettings(server_port=8080)
    assert loopback_base_url(settings) == "http://127.0.0.1:8080"


def test_advertised_base_url_with_public_host() -> None:
    settings = RuntimeSettings(public_host="192.168.1.10", public_port=9090)
    assert advertised_base_url(settings) == "http://192.168.1.10:9090"


def test_advertised_base_url_fallback() -> None:
    settings = RuntimeSettings(server_port=8081)
    url = advertised_base_url(settings)
    assert "8081" in url


# ── profile_service ───────────────────────────────────────────────────


def test_precompute_profiles_empty() -> None:
    assert precompute_profiles([]) == {}


def test_precompute_profiles_with_models() -> None:
    models = [
        Model(id=1, name="test.gguf", local_path="/m/test.gguf", size_bytes=1024),
        Model(id=2, name="no_path.gguf", local_path=None),
    ]
    profiles = precompute_profiles(models)
    assert 1 in profiles
    assert 2 not in profiles


@patch("app.services.profile_service.get_model_or_404")
def test_get_model_profile(mock_get: MagicMock) -> None:
    mock_get.return_value = Model(
        id=1,
        name="qwen2-7b-q4.gguf",
        local_path="/m/qwen2-7b-q4.gguf",
        size_bytes=4 * 1024**3,
    )
    result = get_model_profile(1)
    assert result["model_id"] == 1
    assert "profile" in result
    assert result["profile"]["family"] == "qwen"


# ── curl_service ──────────────────────────────────────────────────────


@patch("app.services.curl_service.get_server_status", return_value={"status": "stopped"})
def test_build_curl_examples_not_running(mock_status: MagicMock) -> None:
    examples = build_curl_examples()
    assert examples == {"localhost": {}, "lan": {}}


@patch("app.services.curl_service.get_server_status")
@patch("app.services.curl_service.load_runtime_settings")
def test_build_curl_examples_running(
    mock_load: MagicMock,
    mock_status: MagicMock,
) -> None:
    mock_load.return_value = RuntimeSettings(server_port=8080, alias="test-model", api_key="")
    mock_status.return_value = {
        "status": "running",
        "state": {"alias": "test-model", "api_key": ""},
    }
    examples = build_curl_examples()
    assert "localhost" in examples
    assert "lan" in examples
    assert "health" in examples["localhost"]


# ── model_service ─────────────────────────────────────────────────────


@patch("app.services.model_service.scan_model_files", return_value=["/m/a.gguf", "/m/b.gguf"])
@patch("app.services.model_service.bulk_upsert_from_scan", return_value=2)
def test_import_local_models(mock_bulk: MagicMock, mock_scan: MagicMock) -> None:
    result = import_local_models()
    assert result == 2
    mock_scan.assert_called_once()
    mock_bulk.assert_called_once_with(["/m/a.gguf", "/m/b.gguf"])


@patch("app.services.model_service.get_model_or_404")
@patch("app.db.session_scope")
@patch("app.services.model_service.queue")
@patch("app.services.model_service.download_model")
@patch("app.repositories.job_repo.create_job")
@patch("app.repositories.job_repo.update_job")
def test_enqueue_download(
    mock_update: MagicMock,
    mock_create: MagicMock,
    mock_task: MagicMock,
    mock_queue: MagicMock,
    mock_db: MagicMock,
    mock_get: MagicMock,
) -> None:
    mock_get.return_value = Model(id=5, name="test.gguf")
    mock_create.return_value = MagicMock(id=10)
    mock_job = MagicMock()
    mock_job.id = "rq-1"
    mock_queue.enqueue.return_value = mock_job

    job_id = enqueue_download(5)
    assert job_id == 10
    mock_queue.enqueue.assert_called_once()
