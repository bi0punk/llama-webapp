# Llama Control Center LAN - Nativo Linux

Aplicación web para gestionar modelos GGUF y levantar `llama-server` desde una interfaz FastAPI, con foco en Linux nativo. La idea es simple: eliges el binario `llama-server`, defines la carpeta de modelos, levantas el servidor desde la web, ves logs y dejas el endpoint disponible para otras máquinas de la misma red.

## Qué cubre esta versión

- Buscar binarios `llama-server`, `llama-run`, `llama-cli` en el sistema.
- Configurar carpeta de modelos persistente.
- Escanear e importar modelos `.gguf` ya existentes.
- Iniciar y detener `llama-server` desde la web.
- Ver el log del servidor y refrescar el tail automáticamente.
- Aplicar ajustes sugeridos por modelo: `threads`, `ctx-size`, `-ngl`, `extra_args`.
- Exponer una URL LAN clara para consumo desde otra máquina.
- Generar ejemplos de `curl` para pruebas rápidas.
- Ejecutarse como servicio `systemd` en Linux.

## Flujo operativo real

1. La UI corre en `http://IP_DEL_HOST:8000`.
2. Desde la UI eliges el binario `llama-server` y un modelo `.gguf`.
3. La UI inicia `llama-server` con los parámetros definidos.
4. El servidor LLM queda accesible por LAN en `http://IP_DEL_HOST:8081`.
5. Otra máquina de la red puede consumir el endpoint OpenAI-compatible.

## Requisitos

- Linux nativo
- Python 3.10+
- Redis local si usarás descargas en background
- `llama.cpp` compilado o instalado en el host

Rutas donde la aplicación intentará encontrar `llama-server`:

- `/usr/local/bin`
- `/usr/bin`
- `~/opt/llama.cpp/build/bin`
- `~/llama.cpp/build/bin`
- `~/.local/bin`

## Bootstrap inicial

```bash
cd /ruta/del/proyecto
./scripts/bootstrap_native_linux.sh
```

Eso crea el `.venv`, instala dependencias y deja directorios base.

## Redis local

Si quieres descargar modelos desde la UI o usar la cola de jobs:

```bash
sudo apt-get update
sudo apt-get install -y redis-server
sudo systemctl enable --now redis-server
```

Si solo vas a usar modelos ya presentes en disco, el worker no es obligatorio, pero Redis sigue siendo recomendable para mantener el proyecto consistente.

## Arranque manual

### Web

```bash
./scripts/start_web.sh
```

### Worker

```bash
./scripts/start_worker.sh
```

## Configuración desde la UI

Abre:

- `http://IP_DE_TU_MAQUINA:8000/server`

Luego configura:

- `Bind host = 0.0.0.0`
- `Puerto servidor = 8081`
- `Host LAN publicado = IP real del equipo`
- `Binario = ruta real de llama-server`
- `Carpeta de modelos = ruta donde guardas los .gguf`

Después:

1. Escanea o importa modelos locales.
2. Selecciona uno.
3. Opcionalmente aplica el perfil sugerido.
4. Inicia `llama-server`.
5. Revisa logs desde la misma pantalla.

## Ejemplos de curl

### Desde la misma máquina

```bash
curl -s http://127.0.0.1:8081/health
curl -s http://127.0.0.1:8081/v1/models
curl -s http://127.0.0.1:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama-local","messages":[{"role":"user","content":"Hola"}],"temperature":0.2}'
```

### Desde otra máquina en la LAN

```bash
curl -s http://IP_DE_TU_SERVIDOR:8081/health
curl -s http://IP_DE_TU_SERVIDOR:8081/v1/models
curl -s http://IP_DE_TU_SERVIDOR:8081/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama-local","messages":[{"role":"user","content":"Dame un resumen técnico"}],"temperature":0.2}'
```

## Instalar como servicio systemd

Primero asegúrate de haber hecho bootstrap:

```bash
./scripts/bootstrap_native_linux.sh
```

Luego instala los servicios:

```bash
sudo ./scripts/install_systemd.sh
```

Eso crea:

- `llm-control-center-web.service`
- `llm-control-center-worker.service`
- `deploy/systemd/llm-control-center.env`

### Comandos útiles

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now llm-control-center-web
sudo systemctl enable --now llm-control-center-worker
sudo systemctl status llm-control-center-web
sudo systemctl status llm-control-center-worker
sudo journalctl -u llm-control-center-web -f
sudo journalctl -u llm-control-center-worker -f
```

### Si no quieres instalar el worker

```bash
sudo INSTALL_WORKER=no ./scripts/install_systemd.sh
sudo systemctl enable --now llm-control-center-web
```

## Logs

Logs propios del proyecto:

- `data/logs/llama_server.log`
- `data/logs/job_<id>.log`

Logs de systemd:

```bash
sudo journalctl -u llm-control-center-web -f
sudo journalctl -u llm-control-center-worker -f
```

## Consideraciones de producción

1. `llama-server` seguirá siendo gestionado por la UI. El servicio systemd mantiene viva la aplicación web y el worker.
2. Si reinicias el host, la UI vuelve automáticamente; luego puedes volver a iniciar el modelo desde la web.
3. Si después quieres autolevantar el último modelo al boot, eso se puede agregar como siguiente mejora.
4. Si expones `8081` a toda la LAN, revisa firewall y segmentación.
5. En CPU-only conviene partir con modelos cuantizados moderados y `--parallel 1` si priorizas estabilidad.

## Estructura útil

- `scripts/bootstrap_native_linux.sh`: prepara entorno Python.
- `scripts/start_web.sh`: arranque estable para web.
- `scripts/start_worker.sh`: arranque estable para worker.
- `scripts/install_systemd.sh`: instala servicios systemd.
- `deploy/systemd/*.service`: plantillas de referencia.
- `examples/curl_examples.sh`: ejemplos de consumo.

## Siguiente mejora lógica

Agregar modo “autostart último modelo” para que, tras reinicio del host, `llama-server` vuelva a levantar automáticamente con el último `.gguf` usado.
