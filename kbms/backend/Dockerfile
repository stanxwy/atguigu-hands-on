# syntax=docker/dockerfile:1

# Base image matches pyproject.toml: requires-python = ">=3.11"
FROM python:3.11-slim

# Python / runtime environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10

WORKDIR /app

# Use the Tencent Cloud Debian mirror and install system build dependencies.
# build-essential/git are required to compile some Python wheels (e.g.
# tokenizers, numpy); libgomp1 is needed by OpenMP-backed libraries.
RUN sed -i \
        's|http://deb.debian.org/debian|http://mirrors.tencentyun.com/debian|g; \
         s|http://deb.debian.org/debian-security|http://mirrors.tencentyun.com/debian-security|g' \
        /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Install uv (the project's package manager) via pip using the configured mirror.
RUN pip install --no-cache-dir --upgrade pip uv

# Copy only the dependency manifests first so this layer is cached unless
# pyproject.toml / uv.lock change. The build context is now the `app/` service
# root (see docker-compose.yml `build.context: .`), so these files sit next to
# the Dockerfile.
COPY pyproject.toml uv.lock ./

# Install the third-party dependencies declared in pyproject.toml, honoring the
# exact versions pinned in uv.lock for reproducible builds.
#   --no-install-project : the application source is copied in separately (as the
#                          `app` package) and is NOT installed as a distribution,
#                          so uv never needs to build the project.
#   --frozen             : do not re-resolve; use uv.lock exactly as committed.
# The cache mount keeps uv's download cache out of the image layers.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --frozen

# Activate the uv-managed virtual environment for all subsequent steps and at runtime.
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy the application source. The `app/` directory's modules (api, core, domain,
# ...) form the importable `app` package — the code uses `from app.api...` /
# `from app.workflows...` — so we place them under /app/app and rely on
# PYTHONPATH=/app to make `import app` resolve to /app/app (a namespace package).
# Only the runtime package directories are copied; dev-only files (pyproject.toml,
# uv.lock, Dockerfile, docker-compose.yml, .env, test/, tree.ps1) stay out of the
# image because they are not in this COPY list (and .dockerignore excludes caches).
COPY api app core domain factories infra main.py schema scripts services static utils workflows /app/app/

# Runtime directories used by the import/query services.
RUN mkdir -p /app/temp-files /app/logs

# Import service listens on 8000, query service on 8001.
EXPOSE 8000 8001

# Default: start the application (serves all routers: health / ui / ingest /
# query / task). docker-compose.yml overrides this per service with the target port.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
