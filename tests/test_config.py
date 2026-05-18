from pathlib import Path

from app.config import DATA_DIR, PROJECT_DIR


def test_data_dir_default_is_relative():
    assert DATA_DIR
    data_path = Path(DATA_DIR)
    assert data_path.is_absolute()
    assert str(PROJECT_DIR) in DATA_DIR


def test_project_dir():
    assert PROJECT_DIR.exists()
    assert (PROJECT_DIR / "app").exists()
