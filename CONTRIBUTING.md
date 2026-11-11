# Contribuir

Rama de trabajo: `dev`. `main` recibe merges `--no-ff` con CI verde.

## Entorno

```bash
git clone https://github.com/bi0punk/llama-webapp.git
cd llama-webapp
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
```

## Flujo

```
main  ←  merge --no-ff  ←  dev  ←  feat/* | fix/* | docs/*
```

Commits atómicos en imperativo (`feat`, `fix`, `refactor`, `test`, `docs`,
`build`, `ci`, `chore`). PR contra `dev`.

## Calidad

```bash
ruff check .
mypy app/ worker.py
pytest -q --cov=app --cov=worker --cov-fail-under=75
pip-audit
```

## Tests

- `tests/test_*.py` — configuración, servicios, rutas, repositorios, tareas.
- `tests/test_integration.py` — ciclo start/stop de `llama-server` con TestClient.
- SQLite efímera; no hace falta Redis ni binarios reales.

## Estilo

- Python 3.12+, tipado estricto (`mypy --strict`).
- `logging`, sin `print` en la app.
- Los procesos externos se testean con mocks.

## Documentación

`docs/CONFIGURATION.md`, `docs/DEPLOYMENT.md`, `docs/TROUBLESHOOTING.md`.
