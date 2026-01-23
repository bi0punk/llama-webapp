# Llama Web Model Hub (MVP)

Web app para:
- Registrar modelos (URL directa, ideal para archivos GGUF)
- Descargarlos en segundo plano (RQ + Redis)
- Ejecutar **llama-run** desde una interfaz web con streaming

## Requisitos
- Docker + Docker Compose

## Quickstart

1) Copia el ejemplo de variables de entorno:

```bash
cp .env.example .env
```

2) (Opcional) si el modelo es privado/gated, define tu token (recomendado hacerlo en el entorno):

```bash
export HUGGING_FACE_TOKEN=hf_xxxxxxxxxxxxxxxxx
```

3) Levanta la plataforma:

```bash
docker compose up --build
```

4) Abre la UI:
- http://localhost:8000/models

## Flujo típico

1. En **Modelos** agrega un modelo con URL directa (HF `resolve/main/...gguf?download=true`).
2. Click **Descargar**.
3. Revisa el progreso en **Jobs**.
4. Cuando el modelo queda en **READY**, entra a **Chat**.

## Datos persistentes
Se guardan en `./data`:
- `./data/models` (modelos descargados)
- `./data/logs` (logs de jobs)
- `./data/app.db` (SQLite)

## Notas de rendimiento
- Modelos grandes (20B) en CPU requieren mucha RAM y van lentos. Para producción, añade flags y/o GPU layers.
- Este MVP ejecuta `llama-run` por request (stateless). Luego lo podemos evolucionar a modo servidor con contexto.



## Modelos sugeridos (seed)
La pantalla **Modelos** muestra una lista de modelos “listos para descargar” definida en:

- `app/model_registry.json`

Puedes:
- **Agregar** (solo registra en DB)
- **Agregar + Descargar** (crea el modelo y lanza el job)

Si un modelo es **gated/privado**, debes definir `HUGGING_FACE_TOKEN` (y reiniciar los contenedores).
