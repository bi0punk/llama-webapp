# Despliegue

Dos procesos: **web** (FastAPI + UI) y **worker** (RQ), con **Redis** como
broker. Los contenedores publicados corren como uid 10001.

> Las imágenes publicadas usan **Python 3.15**. Para el entorno local se recomienda 3.12+.

## 1. Docker Compose (recomendado)

```bash
git clone https://github.com/bi0punk/llama-webapp.git
cd llama-webapp
cp .env.example .env
# edita .env: DATA_DIR, REDIS_URL, WEB_TOKEN, LLAMA_*_BIN
docker compose up -d --build
docker compose ps
```

- Web: <http://localhost:8000>
- Redis: `localhost:6379` (solo si lo publicas)

Servicios:

| Servicio | Imagen | Rol |
|---|---|---|
| `redis` | `redis:7-alpine` | Broker de RQ (healthcheck `redis-cli ping`) |
| `web` | `ghcr.io/bi0punk/llama-webapp` | FastAPI, UI, API, spawn de `llama-server` |
| `worker` | `ghcr.io/bi0punk/llama-webapp-worker` | Descargas y tareas largas |

Las imágenes de GHCR corresponden a la **versión 1.0.0** (histórico); el compose
local las construye con `build:`.

Volúmenes: `data_vol` (SQLite, logs, settings) y `models_vol` (GGUF). El binario
de `llama.cpp` se monta desde el host:

```yaml
- ${LLAMA_BIN_DIR:-/usr/local/bin}:/opt/llama/bin:ro
```

Si no tienes el binario en el host, compila `llama.cpp` o usa una imagen que lo
incluya y apunta `LLAMA_SERVER_BIN` al ejecutable.

## 2. Imágenes publicadas (GHCR)

```bash
docker login ghcr.io -u bi0punk
docker pull ghcr.io/bi0punk/llama-webapp:latest
docker pull ghcr.io/bi0punk/llama-webapp-worker:latest
```

En `main` se publica `:latest`; los tags `vX.Y.Z` generan `:X.Y.Z`.

## 3. systemd (Linux nativo)

El repo incluye unidades en `deploy/systemd/` y un instalador:

```bash
sudo ./scripts/install_systemd.sh
```

Variables del servicio: `deploy/systemd/llm-control-center.env` (a partir del
`.env.example`). Unidades:

- `llm-control-center-web.service` → `scripts/start_web.sh` (`WEB_HOST/WEB_PORT`).
- `llm-control-center-worker.service` → `scripts/start_worker.sh`.

```bash
sudo systemctl status llm-control-center-web llm-control-center-worker
sudo journalctl -u llm-control-center-web -f
```

## 4. Permisos y datos

- `DATA_DIR` y `DEFAULT_MODELS_DIR` deben ser escribibles por el usuario del
  servicio (uid 10001 en Docker).
- Con volúmenes nombrados, Docker hereda el dueño de la imagen; con bind mounts:

```bash
sudo chown -R 10001:10001 /srv/llama/data /srv/llama/models
```

- SQLite vive en `DATA_DIR/app.db`; respáldalo junto con
  `runtime_settings.json` y `llama_server_state.json`.

## 5. Actualización

```bash
git pull --ff-only
docker compose build && docker compose up -d
```

La base SQLite se migra sola al arrancar (`Base.metadata.create_all`); para
cambios de esquema destructivos, detén los servicios y guarda una copia.

## 6. Checklist de producción

- [ ] `WEB_TOKEN` definido si la web sale de localhost.
- [ ] `DATA_DIR` y `DEFAULT_MODELS_DIR` con permisos correctos.
- [ ] `llama-server` encontrado (la UI muestra la versión).
- [ ] Redis healthy y worker conectado (`docker compose logs worker`).
- [ ] `/health` responde 200.
- [ ] Modelo GGUF descargado y arrancado desde la UI.
- [ ] Firewall/VPN: no exponer 8000/6379 a internet.
- [ ] Backup de `data_vol` y `models_vol`.
