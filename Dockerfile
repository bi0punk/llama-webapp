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

# Descargar como tarball (más estable que git clone en redes inestables)
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
RUN set -eux; \
    cmake -S . -B build -DCMAKE_BUILD_TYPE=Release; \
    cmake --build build -j"$(nproc)"; \
    ls -lah build/bin || true


#############################
# 2) Runtime Python (web + worker)
#############################
FROM python:3.11-slim AS runtime

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates tini \
    libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# llama.cpp bins
RUN mkdir -p /opt/llama/bin
COPY --from=llama_builder /src/llama.cpp/build/bin/ /opt/llama/bin/
RUN chmod +x /opt/llama/bin/* || true

ENV LLAMA_RUN_BIN=/opt/llama/bin/llama-run
ENV LLAMA_CLI_BIN=/opt/llama/bin/llama-cli
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app/app
COPY worker.py /app/worker.py

EXPOSE 8000
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "app.main"]
