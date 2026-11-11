# Configuración

La app se configura con variables de entorno (`.env`) o con el entorno del
contenedor. `pydantic-settings` las lee al arrancar; las variables exportadas
tienen prioridad sobre `.env`.

Plantilla: [`.env.example`](../.env.example).

## Datos y almacenamiento

| Variable | Default | Descripción |
|---|---|---|
| `DATA_DIR` | `data/` del repo | SQLite, logs, `runtime_settings.json` y estado del servidor |
| `DATABASE_URL` | `sqlite:///$DATA_DIR/app.db` | URL de SQLAlchemy |
| `LOGS_DIR` | `$DATA_DIR/logs` | Logs de `llama-server` y jobs |
| `SETTINGS_PATH` | `$DATA_DIR/runtime_settings.json` | Ajustes editables desde la web |
| `SERVER_STATE_PATH` | `$DATA_DIR/llama_server_state.json` | Último modelo/puerto levantado |
| `DEFAULT_MODELS_DIR` | `$DATA_DIR/models` | Carpeta de modelos GGUF |
| `SQLITE_POOL_SIZE` | `5` | Pool de conexiones SQLite |
| `SQLITE_POOL_TIMEOUT` | `15` | Timeout del pool (s) |
| `SQLITE_MAX_OVERFLOW` | `10` | Conexiones extra |
| `MODELS_PAGE_SIZE` | `100` | Modelos por página |

## Cola de trabajos

| Variable | Default | Descripción |
|---|---|---|
| `REDIS_URL` | `redis://127.0.0.1:6379/0` | Broker de RQ |
| `REDIS_PASSWORD` | vacío | Password de Redis |

Las descargas de Hugging Face y otras tareas largas se encolan en `default` y las
procesa `worker.py`.

## Binarios de llama.cpp

| Variable | Default | Descripción |
|---|---|---|
| `LLAMA_SERVER_BIN` | `/opt/llama/bin/llama-server` | Binario del servidor |
| `LLAMA_RUN_BIN` | `/opt/llama/bin/llama-run` | Runner CLI |
| `LLAMA_CLI_BIN` | `/opt/llama/bin/llama-cli` | CLI |
| `LLAMA_SEARCH_PATHS` | vacío (`:`-separado) | Rutas extra donde buscar binarios |
| `MODEL_SCAN_PATHS` | vacío (`:`-separado) | Rutas extra donde buscar `.gguf` |

La web también descubre binarios en `PATH`, `/opt/llama/bin`, `/usr/local/bin` y
`~/.local/bin`.

## Servidor por defecto

| Variable | Default | Descripción |
|---|---|---|
| `DEFAULT_SERVER_HOST` | `127.0.0.1` | Host donde escucha `llama-server` |
| `DEFAULT_SERVER_PORT` | `8081` | Puerto donde escucha `llama-server` |
| `DEFAULT_SERVER_ALIAS` | `llama-local` | Alias mostrado |
| `DEFAULT_CTX_SIZE` | `4096` | Contexto por defecto |
| `DEFAULT_THREADS` | `4` | Hilos de CPU |
| `DEFAULT_N_GPU_LAYERS` | `0` | Capas en GPU (0 = CPU) |
| `DEFAULT_PUBLIC_HOST` | autodetectado | Host público sugerido |
| `DEFAULT_PUBLIC_PORT` | `8081` | Puerto público sugerido |

## Web y acceso

| Variable | Default | Descripción |
|---|---|---|
| `WEB_HOST` | `127.0.0.1` | Bind de uvicorn (`scripts/start_web.sh`) |
| `WEB_PORT` | `8000` | Puerto de la web |
| `WEB_TITLE` | `Llama Control Center` | Título |
| `WEB_TOKEN` | vacío | Si se define, exige login con ese token |
| `LLAMA_WEB_TOKEN` | vacío | Alias legacy de `WEB_TOKEN` |

> `WEB_TOKEN` y `LLAMA_WEB_TOKEN` son equivalentes; el canónico es `WEB_TOKEN`.
> `/health`, `/login` y `/logout` quedan públicos.

## Hugging Face

| Variable | Default | Descripción |
|---|---|---|
| `HUGGING_FACE_TOKEN` | vacío | Token para modelos con acceso restringido |

## Ejemplos

### LAN con GPU

```env
DATA_DIR=/srv/llama/data
DEFAULT_MODELS_DIR=/srv/llama/models
DEFAULT_SERVER_HOST=0.0.0.0
DEFAULT_SERVER_PORT=8081
DEFAULT_N_GPU_LAYERS=99
DEFAULT_CTX_SIZE=8192
WEB_TOKEN=cambia-este-token
```

### Solo local, sin auth

```env
WEB_HOST=127.0.0.1
WEB_TOKEN=
REDIS_URL=redis://127.0.0.1:6379/0
```
