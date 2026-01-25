# syntax=docker/dockerfile:1.5

#############################
# 1) Build llama.cpp (robusto)
#############################
FROM ubuntu:22.04 AS llama_builder

ARG DEBIAN_FRONTEND=noninteractive
ARG LLAMA_CPP_REF=master

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl tar \
    build-essential cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src

RUN set -eux; \
    rm -rf llama.cpp /tmp/llama.tar.gz; \
    for i in 1 2 3 4 5; do \
      echo "Downloading llama.cpp tarball attempt $i"; \
      curl -L --retry 10 --retry-delay 2 --retry-all-errors \
        -o /tmp/llama.tar.gz "https://github.com/ggerganov/llama.cpp/archive/${LLAMA_CPP_REF}.tar.gz" \
      && break || sleep 2; \
    done; \
    mkdir -p llama.cpp; \
    tar -xzf /tmp/llama.tar.gz -C llama.cpp --strip-components=1; \
    rm -f /tmp/llama.tar.gz

WORKDIR /src/llama.cpp

# Compila y "instala" a /opt/llama dentro del builder
RUN set -eux; \
    cmake -S . -B build \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX=/opt/llama; \
    cmake --build build -j"$(nproc)"; \
    cmake --install build; \
    echo "=== installed tree ==="; \
    find /opt/llama -maxdepth 3 -type f -print; \
    echo "=== ldd llama-cli ==="; \
    (ldd /opt/llama/bin/llama-cli || true)


#############################
# 2) Runtime Python (web + worker)
#############################
FROM python:3.11-slim AS runtime

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini \
    libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copiar instalación completa (bin + libs en ruta conocida)
COPY --from=llama_builder /opt/llama /opt/llama

RUN chmod +x /opt/llama/bin/* || true

# Si hay libs instaladas, que el loader las encuentre
ENV LD_LIBRARY_PATH=/opt/llama/lib:/opt/llama/lib64:${LD_LIBRARY_PATH}

ENV LLAMA_RUN_BIN=/opt/llama/bin/llama-run
ENV LLAMA_CLI_BIN=/opt/llama/bin/llama-cli
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY worker.py /app/worker.py

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "app.main"]
