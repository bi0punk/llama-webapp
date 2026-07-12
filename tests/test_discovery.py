from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.discovery import (
    candidate_binary_paths,
    detect_binary_version,
    find_llama_binaries,
    find_llama_server,
    model_scan_roots,
    scan_model_files,
)
from app.runtime_settings import RuntimeSettings

# ── candidate_binary_paths ───────────────────────────────────────────


@patch("app.discovery.shutil.which", return_value=None)
@patch("app.discovery.load_runtime_settings")
def test_candidate_binary_paths_defaults(
    mock_load: MagicMock,
    mock_which: MagicMock,
) -> None:
    settings = RuntimeSettings(binary_path="")
    mock_load.return_value = settings
    paths = candidate_binary_paths()
    assert len(paths) > 0
    assert all(isinstance(p, str) for p in paths)


@patch("app.discovery.shutil.which", return_value=None)
@patch("app.discovery.load_runtime_settings")
def test_candidate_binary_paths_with_user_setting(
    mock_load: MagicMock,
    mock_which: MagicMock,
) -> None:
    settings = RuntimeSettings(binary_path="/custom/llama-server")
    mock_load.return_value = settings
    paths = candidate_binary_paths()
    assert "/custom/llama-server" in paths
    assert paths[0] == "/custom/llama-server"


@patch("app.discovery.shutil.which")
@patch("app.discovery.load_runtime_settings")
def test_candidate_binary_paths_which_found(
    mock_load: MagicMock,
    mock_which: MagicMock,
) -> None:
    mock_load.return_value = RuntimeSettings(binary_path="")
    mock_which.return_value = "/usr/local/bin/llama-server"
    paths = candidate_binary_paths()
    assert "/usr/local/bin/llama-server" in paths


# ── detect_binary_version ────────────────────────────────────────────


@patch("app.discovery.subprocess.run")
def test_detect_binary_version_success(mock_run: MagicMock) -> None:
    proc = MagicMock()
    proc.stdout = "llama-server version 1.2.3\nbuilt with cmake\n"
    mock_run.return_value = proc
    version = detect_binary_version("/usr/bin/llama-server")
    assert version == "llama-server version 1.2.3"
    mock_run.assert_called_once_with(
        ["/usr/bin/llama-server", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=5,
        check=False,
    )


@patch("app.discovery.subprocess.run", side_effect=Exception("no binary"))
def test_detect_binary_version_failure(mock_run: MagicMock) -> None:
    assert detect_binary_version("/nonexistent") == "desconocida"


# ── find_llama_server ────────────────────────────────────────────────


@patch("app.discovery.shutil.which", return_value="/usr/bin/llama-server")
@patch("app.discovery.detect_binary_version", return_value="llama-server v1.0")
def test_find_llama_server_found(mock_ver: MagicMock, mock_which: MagicMock) -> None:
    result = find_llama_server()
    assert result is not None
    assert result["path"] == "/usr/bin/llama-server"
    assert result["name"] == "llama-server"
    assert result["version"] == "llama-server v1.0"


@patch("app.discovery.shutil.which", return_value=None)
def test_find_llama_server_not_found(mock_which: MagicMock) -> None:
    assert find_llama_server() is None


# ── find_llama_binaries ──────────────────────────────────────────────


@patch("app.discovery.candidate_binary_paths", return_value=["/a/llama-server", "/b/llama-cli"])
@patch("app.discovery.Path.exists")
@patch("app.discovery.detect_binary_version")
def test_find_llama_binaries(
    mock_ver: MagicMock,
    mock_exists: MagicMock,
    mock_paths: MagicMock,
) -> None:
    mock_exists.return_value = True
    mock_ver.side_effect = ["v1", "v2"]
    binaries = find_llama_binaries()
    assert len(binaries) == 2
    assert binaries[0]["name"] == "llama-server"
    assert binaries[1]["name"] == "llama-cli"


# ── model_scan_roots ─────────────────────────────────────────────────


@patch("app.discovery.load_runtime_settings")
def test_model_scan_roots_default(mock_load: MagicMock) -> None:
    settings = RuntimeSettings()
    mock_load.return_value = settings
    roots = model_scan_roots()
    assert len(roots) > 0
    assert all(isinstance(r, str) for r in roots)


@patch("app.discovery.load_runtime_settings")
def test_model_scan_roots_with_user_root(mock_load: MagicMock) -> None:
    settings = RuntimeSettings(model_root_dir="/custom/models")
    mock_load.return_value = settings
    roots = model_scan_roots()
    assert "/custom/models" in roots
    assert roots[0] == "/custom/models"


# ── scan_model_files ─────────────────────────────────────────────────


def test_scan_model_files_finds_gguf(tmp_path: Path) -> None:
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    (sub_dir / "test.gguf").write_bytes(b"gguf")
    (sub_dir / "not_a_model.txt").write_bytes(b"hello")

    settings = RuntimeSettings(model_root_dir=str(tmp_path))
    with (
        patch("app.discovery.load_runtime_settings", return_value=settings),
        patch("app.discovery.DEFAULT_MODEL_SCAN_PATHS", []),
        patch("app.discovery.EXTRA_MODEL_SCAN_PATHS", []),
    ):
        found = scan_model_files(max_depth=2)
    assert len(found) == 1
    assert found[0].endswith("test.gguf")


def test_scan_model_files_respects_max_depth(tmp_path: Path) -> None:
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)
    (deep / "model.gguf").write_bytes(b"gguf")
    (tmp_path / "root.gguf").write_bytes(b"gguf")

    settings = RuntimeSettings(model_root_dir=str(tmp_path))
    with (
        patch("app.discovery.load_runtime_settings", return_value=settings),
        patch("app.discovery.DEFAULT_MODEL_SCAN_PATHS", []),
        patch("app.discovery.EXTRA_MODEL_SCAN_PATHS", []),
    ):
        found = scan_model_files(max_depth=2)
    assert len(found) == 1
    assert found[0].endswith("root.gguf")
