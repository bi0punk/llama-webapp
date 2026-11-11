## Qué cambia

## Por qué

## Cómo se probó

- [ ] `ruff check .`
- [ ] `mypy app/ worker.py`
- [ ] `pytest -q --cov=app --cov=worker --cov-fail-under=75`
- [ ] `docker compose build` (si tocó imagen)

## Checklist

- [ ] Tests nuevos para el cambio
- [ ] Sin tokens, rutas de modelos ni datos personales en el diff
- [ ] Docs actualizadas si aplica
