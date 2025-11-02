# syntax=docker/dockerfile:1.4

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
COPY pyproject.toml pyproject.toml
COPY src ./src

RUN pip install --upgrade pip \
    && pip wheel --no-deps --wheel-dir /wheels -r requirements.txt \
    && pip wheel --no-deps --wheel-dir /wheels .

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENV=production \
    PORT=8050 \
    DATA_DIR=/app/data/raw \
    CACHE_TIMEOUT=300 \
    PATH="/opt/venv/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /bin/bash appuser

COPY --from=builder /wheels /wheels
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir /wheels/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY assets ./assets
COPY data ./data

RUN mkdir -p ${DATA_DIR} && chown -R appuser:appuser /app

USER appuser

EXPOSE 8050

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

CMD ["gunicorn", "mortalidad.app:server", "--bind", "0.0.0.0:8050", "--workers", "2", "--timeout", "60"]
