# Troubleshooting

Orden: **salud → Redis/worker → binario de llama.cpp → modelo → web**.

## 1. La web no arranca o está unhealthy

```bash
docker compose ps
docker compose logs --tail=100 web
curl -fsS http://localhost:8000/health
docker inspect --format '{{.State.Health.Status}}' llama-webapp
```

| Síntoma | Causa | Solución |
|---|---|---|
| `Address already in use` | Puerto 8000 ocupado | Cambia el mapeo o `WEB_PORT` |
| `Permission denied` en `/data` | Volumen de root | `sudo chown -R 10001:10001 data models` |
| `WEB_TOKEN` no pide login | Variable con otro nombre | Usa `WEB_TOKEN` o `LLAMA_WEB_TOKEN` |
| Healthcheck unhealthy | La app no responde | Revisa logs y `DATA_DIR` |

## 2. Redis / worker

```bash
docker compose logs --tail=100 worker
docker compose exec redis redis-cli ping
docker compose exec redis redis-cli llen rq:queue:default
```

| Síntoma | Solución |
|---|---|
| `Connection refused` a Redis | `REDIS_URL` incorrecta o Redis caído |
| Jobs quedan en cola | El worker no corre: revisa `docker compose logs worker` |
| `WRONGPASS` | `REDIS_PASSWORD` distinto entre web y worker |
| Descargas no avanzan | Mira `DATA_DIR/logs/job_<id>.log` |

## 3. Binario de llama.cpp

La UI muestra las rutas detectadas y la versión. Si no aparece:

```bash
which llama-server
docker compose exec web ls -l /opt/llama/bin
docker compose exec web /opt/llama/bin/llama-server --version
```

- Define `LLAMA_SERVER_BIN` con la ruta real.
- Añade la carpeta a `LLAMA_SEARCH_PATHS` (`:`-separado).
- En Docker, monta el binario en `/opt/llama/bin` (el compose ya lo hace) y
  asegúrate de que sea ejecutable por uid 10001.

## 4. Modelos GGUF

| Síntoma | Causa | Solución |
|---|---|---|
| “No es un GGUF válido” | Archivo parcial o corrupto | Borra y vuelve a descargar |
| No aparece en el listado | Fuera de `DEFAULT_MODELS_DIR`/`MODEL_SCAN_PATHS` | Mueve el `.gguf` o ajusta la ruta |
| Descarga 401/403 | Modelo con acceso restringido | Define `HUGGING_FACE_TOKEN` |
| Arranca y muere | RAM/VRAM insuficiente | Baja `DEFAULT_CTX_SIZE`, `DEFAULT_N_GPU_LAYERS` o usa quantización menor |

Los logs del proceso están en `DATA_DIR/logs/` y en la vista de servidor.

## 5. llama-server no responde

```bash
curl -s http://127.0.0.1:8081/health
curl -s http://127.0.0.1:8081/v1/models
```

- El puerto por defecto es `DEFAULT_SERVER_PORT` (8081). Si está ocupado, cambia
  el perfil o el puerto.
- `host 127.0.0.1` solo acepta conexiones locales; para la LAN usa `0.0.0.0`.
- Revisa `data/llama_server_state.json` para ver el último arranque.

## 6. Tests / CI en rojo

```bash
uv venv .venv --python 3.12
uv pip install -e ".[dev]"
.venv/bin/ruff check .
.venv/bin/mypy app/ worker.py
.venv/bin/pytest -q --cov=app --cov=worker --cov-fail-under=75
```

Errores típicos:

- **mypy strict**: añade anotaciones; `ignore_missing_imports` ya está activo.
- **pytest**: los tests usan SQLite efímera y mocks; no levantes `llama-server`.
- **pip-audit**: si aparece un CVE, actualiza la dependencia y vuelve a correr.

## 7. Recolectar diagnóstico

```bash
docker compose ps > diag.txt
docker compose logs --tail=300 >> diag.txt
curl -s localhost:8000/health >> diag.txt
docker compose exec redis redis-cli info >> diag.txt
```

Adjunta `diag.txt`, el commit (`git rev-parse --short HEAD`) y el modelo usado.
