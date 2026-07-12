from __future__ import annotations

import os
import signal
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from app.llama_server_manager import (
    build_server_command,
    cleanup_stale_process,
    clear_server_state,
    get_server_status,
    is_pid_running,
    kill_process_group,
    load_server_state,
    save_server_state,
    server_http_status,
    server_log_tail,
    start_llama_server,
    stop_llama_server,
)
from app.runtime_settings import RuntimeSettings

# ── helpers ──────────────────────────────────────────────────────────


@pytest.fixture
def settings() -> RuntimeSettings:
    return RuntimeSettings(
        server_host="127.0.0.1",
        server_port=8081,
        alias="llama-test",
        ctx_size=4096,
        threads=4,
        n_gpu_layers=0,
        api_key="",
        extra_args="",
    )


@pytest.fixture
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "data"


@pytest.fixture(autouse=True)
def patch_paths(state_dir: Path) -> None:
    with (
        patch("app.llama_server_manager.SERVER_STATE_PATH", str(state_dir / "state.json")),
        patch("app.llama_server_manager.LOGS_DIR", str(state_dir / "logs")),
    ):
        yield


# ── server state (JSON) ──────────────────────────────────────────────


def test_save_and_load_server_state(state_dir: Path) -> None:
    state = {"pid": 1234, "port": 8081}
    save_server_state(state)
    loaded = load_server_state()
    assert loaded == state
    assert (state_dir / "state.json").exists()


def test_load_server_state_missing() -> None:
    assert load_server_state() == {}


def test_load_server_state_corrupt() -> None:
    path = Path("app/llama_server_manager").parent / "data" / "state.json"
    os.makedirs(path.parent, exist_ok=True)
    path.write_text("not-json", encoding="utf-8")
    assert load_server_state() == {}


def test_clear_server_state(state_dir: Path) -> None:
    save_server_state({"pid": 1})
    clear_server_state()
    assert not (state_dir / "state.json").exists()


# ── PID utils ────────────────────────────────────────────────────────


@patch("os.kill")
def test_is_pid_running_true(mock_kill: MagicMock) -> None:
    assert is_pid_running(1234) is True
    mock_kill.assert_called_once_with(1234, 0)


@patch("os.kill", side_effect=OSError)
def test_is_pid_running_false(mock_kill: MagicMock) -> None:
    assert is_pid_running(1234) is False


def test_is_pid_running_none() -> None:
    assert is_pid_running(None) is False


@patch("os.killpg")
@patch("os.kill")
def test_kill_process_group(mock_kill: MagicMock, mock_killpg: MagicMock) -> None:
    kill_process_group(42, signal.SIGTERM)
    mock_killpg.assert_called_once_with(42, signal.SIGTERM)
    mock_kill.assert_called_once_with(42, signal.SIGTERM)


@patch("os.killpg", side_effect=ProcessLookupError)
@patch("os.kill", side_effect=ProcessLookupError)
def test_kill_process_group_suppresses_error(mock_kill: MagicMock, mock_killpg: MagicMock) -> None:
    kill_process_group(9999, signal.SIGTERM)


# ── cleanup_stale_process ────────────────────────────────────────────


@patch("app.llama_server_manager.is_pid_running")
@patch("app.llama_server_manager.kill_process_group")
def test_cleanup_stale_process_running(
    mock_kill: MagicMock,
    mock_running: MagicMock,
    state_dir: Path,
) -> None:
    mock_running.side_effect = [True, False]
    save_server_state({"pid": 99})
    cleanup_stale_process()
    mock_kill.assert_called_once_with(99, signal.SIGTERM)
    assert not (state_dir / "state.json").exists()


@patch("app.llama_server_manager.is_pid_running", return_value=True)
@patch("app.llama_server_manager.kill_process_group")
def test_cleanup_stale_process_needs_sigkill(
    mock_kill: MagicMock,
    mock_running: MagicMock,
    state_dir: Path,
) -> None:
    save_server_state({"pid": 99})
    cleanup_stale_process()
    assert mock_kill.call_count == 2
    mock_kill.assert_has_calls([call(99, signal.SIGTERM), call(99, signal.SIGKILL)])
    assert not (state_dir / "state.json").exists()


@patch("app.llama_server_manager.is_pid_running", return_value=False)
@patch("app.llama_server_manager.kill_process_group")
def test_cleanup_stale_process_not_running(
    mock_kill: MagicMock,
    mock_running: MagicMock,
    state_dir: Path,
) -> None:
    save_server_state({"pid": 99})
    cleanup_stale_process()
    mock_kill.assert_not_called()
    assert not (state_dir / "state.json").exists()


# ── server_log_tail ──────────────────────────────────────────────────


def test_server_log_tail_no_file(state_dir: Path) -> None:
    assert server_log_tail() == "No hay log todavía."


def test_server_log_tail_with_content(state_dir: Path) -> None:
    log_dir = state_dir / "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = log_dir / "llama_server.log"
    log_file.write_text("line1\nline2\nline3\n", encoding="utf-8")
    tail = server_log_tail(lines=2)
    assert tail == "line2\nline3\n"


# ── server_http_status ───────────────────────────────────────────────


@patch("requests.get")
def test_server_http_status_reachable(mock_get: MagicMock) -> None:
    mock_get.return_value.ok = True
    mock_get.return_value.status_code = 200
    result = server_http_status({"port": 8081, "api_key": ""})
    assert result["reachable"] is True
    assert result["http_status"] == 200
    assert result["ok"] is True


@patch("requests.get", side_effect=Exception("timeout"))
def test_server_http_status_unreachable(mock_get: MagicMock) -> None:
    result = server_http_status({"port": 9999, "api_key": ""})
    assert result["reachable"] is False
    assert result["ok"] is False


# ── get_server_status ────────────────────────────────────────────────


@patch("app.llama_server_manager.is_pid_running", return_value=True)
@patch("app.llama_server_manager.server_http_status", return_value={"reachable": True, "ok": True})
def test_get_server_status_running(
    mock_http: MagicMock,
    mock_running: MagicMock,
    state_dir: Path,
) -> None:
    save_server_state({"pid": 42, "port": 8081})
    status = get_server_status()
    assert status["status"] == "running"
    assert status["pid"] == 42


@patch("app.llama_server_manager.is_pid_running", return_value=False)
def test_get_server_status_stopped(mock_running: MagicMock, state_dir: Path) -> None:
    save_server_state({"pid": 42})
    status = get_server_status()
    assert status["status"] == "stopped"


def test_get_server_status_empty_state(state_dir: Path) -> None:
    status = get_server_status()
    assert status["status"] == "stopped"
    assert status["pid"] is None


# ── build_server_command ─────────────────────────────────────────────


def test_build_server_command_basic(settings: RuntimeSettings) -> None:
    cmd = build_server_command("/usr/bin/llama-server", "/models/test.gguf", settings)
    assert cmd[0] == "/usr/bin/llama-server"
    assert "-m" in cmd
    assert cmd[cmd.index("-m") + 1] == "/models/test.gguf"
    assert "--host" in cmd
    assert "--port" in cmd
    assert str(settings.server_port) in cmd


def test_build_server_command_with_gpu(settings: RuntimeSettings) -> None:
    settings.n_gpu_layers = 20
    cmd = build_server_command("/bin/llama-server", "/m.gguf", settings)
    assert "-ngl" in cmd
    assert "20" in cmd


def test_build_server_command_with_api_key(settings: RuntimeSettings) -> None:
    settings.api_key = "sk-test"
    cmd = build_server_command("/bin/llama-server", "/m.gguf", settings)
    assert "--api-key" in cmd
    assert "sk-test" in cmd


def test_build_server_command_with_extra_args(settings: RuntimeSettings) -> None:
    settings.extra_args = "--mlock --no-mmap"
    cmd = build_server_command("/bin/llama-server", "/m.gguf", settings)
    assert "--mlock" in cmd
    assert "--no-mmap" in cmd


def test_build_server_command_invalid_extra_arg(settings: RuntimeSettings) -> None:
    settings.extra_args = "--bad$arg"
    with pytest.raises(ValueError, match="Argumento no permitido"):
        build_server_command("/bin/llama-server", "/m.gguf", settings)


# ── start_llama_server ───────────────────────────────────────────────


@patch("app.llama_server_manager.get_server_status", return_value={"status": "stopped"})
@patch("app.llama_server_manager.subprocess.Popen")
@patch("app.llama_server_manager.is_pid_running", return_value=True)
def test_start_llama_server_success(
    mock_running: MagicMock,
    mock_popen: MagicMock,
    mock_status: MagicMock,
    settings: RuntimeSettings,
    state_dir: Path,
) -> None:
    proc = MagicMock()
    proc.pid = 9999
    proc.poll.return_value = None
    mock_popen.return_value = proc

    result = start_llama_server("/usr/bin/llama-server", "/models/test.gguf", settings, model_id=1)

    assert result["pid"] == 9999
    assert result["model_path"] == "/models/test.gguf"
    assert result["port"] == 8081

    loaded = load_server_state()
    assert loaded["pid"] == 9999


@patch("app.llama_server_manager.get_server_status", return_value={"status": "running"})
def test_start_llama_server_already_running(
    mock_status: MagicMock,
    settings: RuntimeSettings,
) -> None:
    with pytest.raises(RuntimeError, match="Ya existe un llama-server activo"):
        start_llama_server("/bin/llama-server", "/m.gguf", settings)


# ── stop_llama_server ────────────────────────────────────────────────


@patch("app.llama_server_manager.is_pid_running", return_value=True)
@patch("app.llama_server_manager.kill_process_group")
def test_stop_llama_server(
    mock_kill: MagicMock,
    mock_running: MagicMock,
    state_dir: Path,
) -> None:
    save_server_state({"pid": 42})
    result = stop_llama_server()
    assert result["stopped"] is True
    assert not (state_dir / "state.json").exists()


@patch("app.llama_server_manager.is_pid_running", return_value=False)
def test_stop_llama_server_not_running(mock_running: MagicMock, state_dir: Path) -> None:
    save_server_state({"pid": 42})
    result = stop_llama_server()
    assert result["stopped"] is False
