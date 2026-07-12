from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.models import Job, Model
from app.tasks import _download_target_path, _guess_filename_from_url, _safe_filename, download_model

# ── _safe_filename ───────────────────────────────────────────────────


def test_safe_filename_clean() -> None:
    assert _safe_filename("test.gguf") == "test.gguf"


def test_safe_filename_sanitized() -> None:
    assert _safe_filename("my model (2).gguf") == "my_model_2_.gguf"


def test_safe_filename_adds_extension() -> None:
    assert _safe_filename("mymodel").endswith(".gguf")


def test_safe_filename_empty_becomes_default() -> None:
    assert _safe_filename("...") == "model.gguf"


# ── _guess_filename_from_url ─────────────────────────────────────────


def test_guess_filename_from_url_direct() -> None:
    name = _guess_filename_from_url("https://example.com/models/llama-2-7b.Q4_K_M.gguf")
    assert name == "llama-2-7b.Q4_K_M.gguf"


def test_guess_filename_from_url_fallback() -> None:
    assert _guess_filename_from_url("https://example.com/").endswith(".gguf")


# ── _download_target_path ────────────────────────────────────────────


@patch("app.tasks.load_runtime_settings")
def test_download_target_path(mock_load: MagicMock, tmp_path: Path) -> None:
    settings = MagicMock()
    settings.model_root_dir = str(tmp_path)
    mock_load.return_value = settings

    model = MagicMock()
    model.name = "test.gguf"

    result = _download_target_path(model)
    assert result == tmp_path / "test.gguf"
    assert tmp_path.exists()


# ── helpers ──────────────────────────────────────────────────────────


def _make_job() -> MagicMock:
    job = MagicMock(spec=Job)
    job.id = 1
    job.log_path = ""
    job.status = "queued"
    job.progress = 0
    job.message = ""
    job.rq_job_id = None
    job.type = "download"
    return job


def _make_model(name: str = "test.gguf", url: str = "https://example.com/model.gguf") -> MagicMock:
    model = MagicMock(spec=Model)
    model.id = 1
    model.name = name
    model.url = url
    model.status = "NEW"
    model.local_path = None
    model.size_bytes = None
    model.source_type = "direct_url"
    return model


def _mock_session(job: MagicMock | None, model: MagicMock | None) -> MagicMock:
    mapping: dict[type, MagicMock] = {}
    if job is not None:
        mapping[Job] = job
    if model is not None:
        mapping[Model] = model

    session = MagicMock()
    session.get.side_effect = lambda cls, pk: mapping.get(cls)
    return session


def _make_response(
    status_code: int = 200,
    content: bytes = b"x" * 100,
    content_type: str = "application/octet-stream",
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = status_code == 200
    resp.url = "https://example.com/model.gguf"
    resp.headers = {"Content-Type": content_type, "Content-Length": str(len(content))}
    resp.iter_content = lambda chunk_size=None, **kwargs: iter([content])
    return resp


# ── download_model scenarios ─────────────────────────────────────────


@patch("app.tasks.os.makedirs")
@patch("app.tasks.session_scope")
def test_download_model_no_job(mock_scope: MagicMock, mock_makedirs: MagicMock) -> None:
    session = _mock_session(None, None)
    mock_scope.return_value.__enter__.return_value = session
    assert download_model(1, 1) is None


@patch("app.tasks.os.makedirs")
@patch("app.tasks.session_scope")
def test_download_model_no_url(mock_scope: MagicMock, mock_makedirs: MagicMock) -> None:
    job = _make_job()
    model = _make_model(url=None)

    session = _mock_session(job, model)
    mock_scope.return_value.__enter__.return_value = session

    download_model(1, 1)
    assert model.status == "ERROR"


@patch("app.tasks.os.path.getsize", return_value=100)
@patch("app.tasks.validate_gguf_header", return_value=(True, "GGUF v3"))
@patch("app.tasks.load_runtime_settings")
@patch("app.tasks.requests.Session")
@patch("app.tasks.os.replace")
@patch("app.tasks.session_scope")
def test_download_model_success(
    mock_scope: MagicMock,
    mock_replace: MagicMock,
    mock_requests: MagicMock,
    mock_load: MagicMock,
    mock_validate: MagicMock,
    mock_getsize: MagicMock,
    tmp_path: Path,
) -> None:
    job = _make_job()
    model = _make_model()

    settings = MagicMock()
    settings.model_root_dir = str(tmp_path / "models")
    mock_load.return_value = settings

    session = _mock_session(job, model)
    mock_scope.return_value.__enter__.return_value = session

    response = _make_response()
    mock_requests.return_value.__enter__.return_value.get.return_value.__enter__.return_value = response

    download_model(1, 1)

    assert job.status == "done"
    assert job.progress == 100
    assert model.status == "READY"


@patch("app.tasks.validate_gguf_header", return_value=(True, "GGUF v3"))
@patch("app.tasks.requests.Session")
@patch("app.tasks.os.replace")
@patch("app.tasks.os.makedirs")
@patch("app.tasks.session_scope")
def test_download_model_http_401(
    mock_scope: MagicMock,
    mock_makedirs: MagicMock,
    mock_replace: MagicMock,
    mock_requests: MagicMock,
    mock_validate: MagicMock,
) -> None:
    job = _make_job()
    model = _make_model()

    session = _mock_session(job, model)
    mock_scope.return_value.__enter__.return_value = session

    response = _make_response(status_code=401)
    mock_requests.return_value.__enter__.return_value.get.return_value.__enter__.return_value = response

    download_model(1, 1)
    assert model.status == "NEEDS_TOKEN"


@patch("app.tasks.validate_gguf_header", return_value=(True, "GGUF v3"))
@patch("app.tasks.requests.Session")
@patch("app.tasks.os.replace")
@patch("app.tasks.os.makedirs")
@patch("app.tasks.session_scope")
def test_download_model_http_429(
    mock_scope: MagicMock,
    mock_makedirs: MagicMock,
    mock_replace: MagicMock,
    mock_requests: MagicMock,
    mock_validate: MagicMock,
) -> None:
    job = _make_job()
    model = _make_model()

    session = _mock_session(job, model)
    mock_scope.return_value.__enter__.return_value = session

    response = _make_response(status_code=429)
    mock_requests.return_value.__enter__.return_value.get.return_value.__enter__.return_value = response

    download_model(1, 1)
    assert model.status == "ERROR"


@patch("app.tasks.validate_gguf_header", return_value=(True, "GGUF v3"))
@patch("app.tasks.requests.Session")
@patch("app.tasks.os.replace")
@patch("app.tasks.os.makedirs")
@patch("app.tasks.session_scope")
def test_download_model_html_response(
    mock_scope: MagicMock,
    mock_makedirs: MagicMock,
    mock_replace: MagicMock,
    mock_requests: MagicMock,
    mock_validate: MagicMock,
) -> None:
    job = _make_job()
    model = _make_model()

    session = _mock_session(job, model)
    mock_scope.return_value.__enter__.return_value = session

    response = _make_response(content=b"<html>not gguf</html>", content_type="text/html")
    mock_requests.return_value.__enter__.return_value.get.return_value.__enter__.return_value = response

    download_model(1, 1)
    assert job.status == "error"


@patch("app.tasks.validate_gguf_header", return_value=(False, "Bad GGUF"))
@patch("app.tasks.requests.Session")
@patch("app.tasks.os.replace")
@patch("app.tasks.os.makedirs")
@patch("app.tasks.session_scope")
def test_download_model_invalid_gguf(
    mock_scope: MagicMock,
    mock_makedirs: MagicMock,
    mock_replace: MagicMock,
    mock_requests: MagicMock,
    mock_validate: MagicMock,
) -> None:
    job = _make_job()
    model = _make_model()

    session = _mock_session(job, model)
    mock_scope.return_value.__enter__.return_value = session

    response = _make_response()
    mock_requests.return_value.__enter__.return_value.get.return_value.__enter__.return_value = response

    download_model(1, 1)
    assert model.status == "ERROR"
    assert job.status == "error"
