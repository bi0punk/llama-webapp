from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.models import Job, Model
from app.repositories.job_repo import create_job, get_jobs, update_job
from app.repositories.model_repo import (
    create_model,
    delete_model,
    get_model_or_404,
    get_models_page,
    model_exists,
    serialize_model,
)
from app.repositories.registry_repo import load_registry


# ── model_repo ────────────────────────────────────────────────────────


def test_serialize_model() -> None:
    model = Model(id=1, name="test.gguf", status="READY", local_path="/m/test.gguf", url="")
    result = serialize_model(model)
    assert result["id"] == 1
    assert result["name"] == "test.gguf"
    assert result["status"] == "READY"
    assert result["local_path"] == "/m/test.gguf"
    assert result["url"] == ""


@patch("app.repositories.model_repo.session_scope")
def test_get_models_page(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_query = mock_session.query.return_value
    mock_query.count.return_value = 2
    mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        Model(id=1, name="a"),
        Model(id=2, name="b"),
    ]
    models, total = get_models_page(page=1, page_size=10)
    assert total == 2
    assert len(models) == 2


@patch("app.repositories.model_repo.session_scope")
def test_get_model_or_404_found(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_session.get.return_value = Model(id=42, name="test")
    model = get_model_or_404(42)
    assert model.id == 42
    assert model.name == "test"


@patch("app.repositories.model_repo.session_scope")
def test_get_model_or_404_not_found(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_session.get.return_value = None
    with pytest.raises(Exception):
        get_model_or_404(999)


@patch("app.repositories.model_repo.session_scope")
def test_model_exists(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_session.query.return_value.all.return_value = [
        Model(name="a", url="u1"),
        Model(name="b", url="u2"),
    ]
    assert model_exists("a", "u1") is True
    assert model_exists("c", "u3") is False


@patch("app.repositories.model_repo.session_scope")
def test_create_model(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_session.get.return_value = Model(id=99, name="new", url="http://example.com/model")
    model = create_model("new", "http://example.com/model", "direct_url")
    assert model.id == 99
    assert model.name == "new"


@patch("app.repositories.model_repo.session_scope")
def test_delete_model(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_session.get.return_value = Model(id=1, name="test", local_path=None)
    delete_model(1)
    mock_session.delete.assert_called_once()


# ── job_repo ──────────────────────────────────────────────────────────


@patch("app.repositories.job_repo.session_scope")
def test_get_jobs(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_session.query.return_value.order_by.return_value.limit.return_value.all.return_value = [
        Job(id=1, type="download"),
        Job(id=2, type="download"),
    ]
    jobs = get_jobs(limit=2)
    assert len(jobs) == 2


@patch("app.repositories.job_repo.session_scope")
def test_create_job(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_session.get.return_value = Job(id=7, type="download", status="queued")
    job = create_job(type_="download", message="test")
    assert job.id == 7
    assert job.type == "download"


@patch("app.repositories.job_repo.session_scope")
def test_update_job(mock_scope: MagicMock) -> None:
    mock_session = MagicMock()
    mock_scope.return_value.__enter__.return_value = mock_session
    mock_job = MagicMock(spec=Job)
    mock_session.get.return_value = mock_job
    update_job(1, status="running", rq_job_id="abc")
    assert mock_job.status == "running"
    assert mock_job.rq_job_id == "abc"


# ── registry_repo ─────────────────────────────────────────────────────


def test_load_registry_no_file(tmp_path: Path) -> None:
    reg_path = tmp_path / "model_registry.json"
    assert not reg_path.exists()
    result = load_registry()
    assert result == []


@patch("app.repositories.registry_repo.BASE_DIR")
def test_load_registry_invalid_json(mock_base: MagicMock) -> None:
    reg_path = MagicMock(spec=Path)
    reg_path.exists.return_value = True
    reg_path.read_text.return_value = "not json"
    mock_base.__truediv__.return_value = reg_path
    result = load_registry()
    assert result == []
