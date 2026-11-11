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


def test_web_token_acepta_alias_legacy(monkeypatch):
    """El .env.example documentaba LLAMA_WEB_TOKEN; debe seguir funcionando."""
    monkeypatch.delenv("WEB_TOKEN", raising=False)
    monkeypatch.setenv("LLAMA_WEB_TOKEN", "token-legacy")
    from app.config import Settings

    assert Settings().web_token == "token-legacy"


def test_web_token_canonico_tiene_prioridad(monkeypatch):
    monkeypatch.setenv("WEB_TOKEN", "canonico")
    monkeypatch.setenv("LLAMA_WEB_TOKEN", "legacy")
    from app.config import Settings

    assert Settings().web_token == "canonico"
