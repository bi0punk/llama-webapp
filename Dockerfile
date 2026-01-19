# syntax=docker/dockerfile:1

# --- Stage 1: build llama.cpp (llama-run) ---
FROM ubuntu:22.04 AS llama_builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --depth 1 https://github.com/ggerganov/llama.cpp.git
WORKDIR /src/llama.cpp
RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build build -j"$(nproc)"

# --- Stage 2: runtime ---
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini \
    && rm -rf /var/lib/apt/lists/*

# llama.cpp binaries
COPY --from=llama_builder /src/llama.cpp/build/bin/llama-run /usr/local/bin/llama-run
COPY --from=llama_builder /src/llama.cpp/build/bin/llama-cli /usr/local/bin/llama-cli

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY worker.py /app/worker.py

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "app.main"]
