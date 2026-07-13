from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from app.discovery import model_scan_roots, scan_model_files
from app.runtime_settings import RuntimeSettings


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
