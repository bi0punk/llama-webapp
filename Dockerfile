# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH=/opt/venv \
    DATA_DIR=/data

RUN python -m venv $VENV_PATH
ENV PATH="$VENV_PATH/bin:$PATH"

WORKDIR /app

COPY pyproject.toml ./
COPY app/ ./app/
RUN pip install --no-cache-dir .

COPY worker.py ./
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin llama \
    && mkdir -p /data /models \
    && chown -R llama:llama /app /data /models

USER llama
EXPOSE 8000

FROM base AS web
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS worker
CMD ["python", "worker.py"]
