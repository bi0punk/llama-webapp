# Llama Control Center LAN

[![CI](https://github.com/bi0punk/llama-webapp/actions/workflows/ci.yml/badge.svg)](https://github.com/bi0punk/llama-webapp/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Aplicación web para gestionar modelos GGUF y levantar `llama-server` desde una interfaz FastAPI, con foco en Linux nativo. La idea es simple: eliges el binario `llama-server`, defines la carpeta de modelos, levantas el servidor desde la web, ves logs y dejas el endpoint disponible para otras máquinas de la misma red.

## Tabla de contenidos

- [Características](#características)
- [Stack](#stack)
- [Arquitectura](#arquitectura)
- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Uso](#uso)
- [Tests](#tests)
- [Configuración](#configuración)
- [CI](#ci)
- [Datos](#datos)
- [Limitaciones y roadmap](#limitaciones-y-roadmap)
- [Licencia](#licencia)

## Características

- Buscar binarios `llama-server`, `llama-run`, `llama-cli` en el sistema.
- Configurar carpeta de modelos persistente.
- Escanear e importar modelos `.gguf` ya existentes.
- Iniciar y detener `llama-server` desde la web.
- Ver el log del servidor y refrescar el tail automáticamente.
- Aplicar ajustes sugeridos por modelo: `threads`, `ctx-size`, `-ngl`, `extra_args`.
- Exponer una URL LAN clara para consumo desde otra máquina.
- Generar ejemplos de `curl` para pruebas rápidas.
- Ejecutarse como servicio `systemd` en Linux.
- Cola de jobs (RQ + Redis) para descargas en background.

## Stack

- **Lenguaje**: Python 3.12+
- **Web**: FastAPI + Uvicorn + Jinja2 (templates HTML, JS vanilla en `app/static/`).
- **Cola**: Redis + RQ (worker separado para descargas/jobs).
- **Persistencia**: SQLAlchemy (SQLite en `data/`).
- **Validación**: Pydantic v2.
- **Calidad**: ruff (lint+format), mypy (no estricto), pytest.
- **Empaquetado**: `pyproject.toml` como única fuente de deps; `setuptools` build backend.
- **Despliegue**: Docker multi-stage (targets `web`/`worker`) + systemd (Linux nativo).

## Arquitectura

```
        ┌──────────────────────────┐         ┌──────────────────────────┐
        │   Navegador (LAN)        │         │   Otra máquina LAN       │
        │   http://HOST:8000       │         │   http://HOST:8081       │
        └────────────┬─────────────┘         └────────────┬─────────────┘
                     │                                    │
                     │ HTTP                               │ OpenAI-compatible API
                     ▼                                    ▼
        ┌──────────────────────────┐         ┌──────────────────────────┐
        │  app (FastAPI + Jinja2)  │  spawn  │  llama-server (binario)  │
        │  uvicorn :8000           ├────────►│  uvicorn/HTTP :8081      │
        │  SQLAlchemy → data/*.db  │         │  modelos .gguf           │
        └────────────┬─────────────┘         └──────────────────────────┘
                     │ encola jobs (descarga)
                     ▼
        ┌──────────────────────────┐
        │  worker.py (RQ Worker)   │
        │  Redis :6379             │
        └──────────────────────────┘
```

- **app** (web): sirve la UI, gestiona el ciclo de vida de `llama-server` (spawn/stop), persiste modelos/ajustes en SQLite y expone endpoints JSON.
- **worker** (RQ): consume la cola Redis para jobs de descarga/limpieza largos; opcional si solo usas modelos ya en disco.
- **llama-server**: proceso externo gestionado por la app; expone la API OpenAI-compatible en el puerto configurado (por defecto 8081).

## Requisitos

- Linux nativo
- Python 3.12+
- Redis local si usarás descargas en background
- `llama.cpp` compilado o instalado en el host

Rutas donde la aplicación intentará encontrar `llama-server`:

- `/usr/local/bin`
- `/usr/bin`
- `~/opt/llama.cpp/build/bin`
- `~/llama.cpp/build/bin`
- `~/.local/bin`

## Instalación

Con `uv` (recomendado):

```bash
cd /ruta/del/proyecto
uv venv -p 3.12 .venv
uv pip install -e ".[dev]"
```

O con `pip` estándar:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Bootstrap completo (crea `.venv`, instala deps y deja directorios base):

```bash
./scripts/bootstrap_native_linux.sh
```

### Redis local

```bash
sudo apt-get update
sudo apt-get install -y redis-server
sudo systemctl enable --now redis-server
```

Si solo vas a usar modelos ya presentes en disco, el worker no es obligatorio, pero Redis sigue siendo recomendable para mantener el proyecto consistente.

## Uso

### Arranque manual

Web:

```bash
./scripts/start_web.sh
```

Worker:

```bash
./scripts/start_worker.sh
```

### Flujo operativo

1. La UI corre en `http://IP_DEL_HOST:8000`.
2. Desde la UI eliges el binario `llama-server` y un modelo `.gguf`.
3. La UI inicia `llama-server` con los parámetros definidos.
4. El servidor LLM queda accesible por LAN en `http://IP_DEL_HOST:8081`.
5. Otra máquina de la red puede consumir el endpoint OpenAI-compatible.

### Ejemplos de curl

Desde la misma máquina:

```bash
curl -s http://127.0.0.1:8081/health
curl -s http://127.0.0.1:8081/v1/models
curl -s http://127.0.0.1:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama-local","messages":[{"role":"user","content":"Hola"}],"temperature":0.2}'
```

Desde otra máquina en la LAN:

```bash
curl -s http://IP_DE_TU_SERVIDOR:8081/health
curl -s http://IP_DE_TU_SERVIDOR:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama-local","messages":[{"role":"user","content":"Dame un resumen técnico"}],"temperature":0.2}'
```

### Instalar como servicio systemd

```bash
./scripts/bootstrap_native_linux.sh
sudo ./scripts/install_systemd.sh
```

Eso crea `llm-control-center-web.service`, `llm-control-center-worker.service` y `deploy/systemd/llm-control-center.env`.

Comandos útiles:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now llm-control-center-web
sudo systemctl enable --now llm-control-center-worker
sudo systemctl status llm-control-center-web
sudo journalctl -u llm-control-center-web -f
```

Sin worker:

```bash
sudo INSTALL_WORKER=no ./scripts/install_systemd.sh
sudo systemctl enable --now llm-control-center-web
```

## Tests

```bash
pytest -v
```

Calidad estática:

```bash
ruff check .
mypy app/ worker.py
```

Cobertura actual:

- `tests/test_config.py` — carga de configuración.
- `tests/test_gguf_validation.py` — validación de cabecera GGUF.
- `tests/test_model_profiles.py` — perfiles y estimación de RAM.
- `tests/test_integration.py` — ciclo start/stop de `llama-server` vía TestClient + `/health`.
- `tests/test_smoke.py` — migración RQ en `worker.py`, render de partials (firma `TemplateResponse`) y endpoints de discovery/curl.

Los tests de integración usan `TestClient` (FastAPI) y levaman una SQLite efímera; no requieren `llama-server` real (se mockea el spawn).

## Configuración

Desde la UI en `http://IP_DE_TU_MAQUINA:8000/server`:

- `Bind host = 0.0.0.0`
- `Puerto servidor = 8081`
- `Host LAN publicado = IP real del equipo`
- `Binario = ruta real de llama-server`
- `Carpeta de modelos = ruta donde guardas los .gguf`

Después: escanea o importa modelos locales → selecciona uno → aplica el perfil sugerido (opcional) → inicia `llama-server` → revisa logs.

Variables de entorno (ver `.env.example`): principalmente `HUGGING_FACE_TOKEN` para descargas. El resto de ajustes runtime se persisten en `data/` vía la UI.

## CI

GitHub Actions (`.github/workflows/ci.yml`) con 4 jobs sobre Python 3.12 / ubuntu-latest, disparados en push y PR a `main`:

- **lint** — `ruff check .` (cubre `app/`, `worker.py`, `tests/`, `scripts/`).
- **typecheck** — `mypy app/ worker.py`.
- **test** — servicio `redis:7-alpine` + `pytest -v`.
- **docker** — `docker build --target web` y `--target worker`.

Usa `actions/setup-python` con `cache: pip` sobre `pyproject.toml`.

## Datos

Directorios y artefactos runtime (todos gitignored salvo `models/.gitkeep`):

- `data/` — SQLite (`*.db`), runtime settings, registros.
- `data/logs/llama_server.log` — log del servidor gestionado.
- `data/logs/job_<id>.log` — log por job de la cola.
- `models/` — carpeta de modelos `.gguf` (vacía por defecto, el usuario la llena).

Logs de systemd:

```bash
sudo journalctl -u llm-control-center-web -f
sudo journalctl -u llm-control-center-worker -f
```

## Consideraciones de producción

1. `llama-server` seguirá siendo gestionado por la UI. El servicio systemd mantiene viva la aplicación web y el worker.
2. Si reinicias el host, la UI vuelve automáticamente; luego puedes volver a iniciar el modelo desde la web.
3. Si expones `8081` a toda la LAN, revisa firewall y segmentación.
4. En CPU-only conviene partir con modelos cuantizados moderados y `--parallel 1` si priorizas estabilidad.

## Estructura del repositorio

- `app/` — aplicación FastAPI (routes, templates, static, modelos, config).
- `worker.py` — worker RQ (cola Redis).
- `tests/` — tests pytest.
- `scripts/` — bootstrap, arranque y systemd.
- `deploy/systemd/` — plantillas de servicios.
- `examples/curl_examples.sh` — ejemplos de consumo.
- `Dockerfile` — multi-stage (targets `web`/`worker`).
- `docker-compose.yml` — orquestación local.
- `pyproject.toml` — única fuente de deps (runtime + `[dev]`).

## Limitaciones y roadmap

- **Limitación**: no hay autostart del último modelo tras reinicio del host.
- **Roadmap**: modo “autostart último modelo” para que, tras boot, `llama-server` vuelva a levantar automáticamente con el último `.gguf` usado.
- **Cobertura de tests**: faltan tests para `routes/`, `llama_server_manager`, `tasks`, `discovery` (los smoke tests actuales cubren lo mínimo).
- **Mypy no estricto**: `disallow_untyped_defs=false`; endurecerlo requiere anotar el código legacy.

## Licencia

MIT — ver [LICENSE](LICENSE).
