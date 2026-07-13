from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from app.runtime_settings import RuntimeSettings
from app.services.binary_service import (
    candidate_binary_paths,
    detect_binary_version,
    find_llama_binaries,
    find_llama_server,
)


@patch("app.services.binary_service.shutil.which", return_value=None)
@patch("app.services.binary_service.load_runtime_settings")
def test_candidate_binary_paths_defaults(
    mock_load: MagicMock,
    mock_which: MagicMock,
) -> None:
    settings = RuntimeSettings(binary_path="")
    mock_load.return_value = settings
    paths = candidate_binary_paths()
    assert len(paths) > 0
    assert all(isinstance(p, str) for p in paths)


@patch("app.services.binary_service.shutil.which", return_value=None)
@patch("app.services.binary_service.load_runtime_settings")
def test_candidate_binary_paths_with_user_setting(
    mock_load: MagicMock,
    mock_which: MagicMock,
) -> None:
    settings = RuntimeSettings(binary_path="/custom/llama-server")
    mock_load.return_value = settings
    paths = candidate_binary_paths()
    assert "/custom/llama-server" in paths
    assert paths[0] == "/custom/llama-server"


@patch("app.services.binary_service.shutil.which")
@patch("app.services.binary_service.load_runtime_settings")
def test_candidate_binary_paths_which_found(
    mock_load: MagicMock,
    mock_which: MagicMock,
) -> None:
    mock_load.return_value = RuntimeSettings(binary_path="")
    mock_which.return_value = "/usr/local/bin/llama-server"
    paths = candidate_binary_paths()
    assert "/usr/local/bin/llama-server" in paths


@patch("app.services.binary_service.subprocess.run")
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


@patch("app.services.binary_service.subprocess.run", side_effect=Exception("no binary"))
def test_detect_binary_version_failure(mock_run: MagicMock) -> None:
    assert detect_binary_version("/nonexistent") == "desconocida"


@patch("app.services.binary_service.shutil.which", return_value="/usr/bin/llama-server")
@patch("app.services.binary_service.detect_binary_version", return_value="llama-server v1.0")
def test_find_llama_server_found(mock_ver: MagicMock, mock_which: MagicMock) -> None:
    result = find_llama_server()
    assert result is not None
    assert result["path"] == "/usr/bin/llama-server"
    assert result["name"] == "llama-server"
    assert result["version"] == "llama-server v1.0"


@patch("app.services.binary_service.shutil.which", return_value=None)
def test_find_llama_server_not_found(mock_which: MagicMock) -> None:
    assert find_llama_server() is None


@patch("app.services.binary_service.candidate_binary_paths", return_value=["/a/llama-server", "/b/llama-cli"])
@patch("pathlib.Path.exists")
@patch("app.services.binary_service.detect_binary_version")
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
