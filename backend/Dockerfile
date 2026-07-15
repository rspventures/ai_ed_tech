# Backend Dockerfile — uv-based, single dependency manifest (pyproject.toml + uv.lock)
FROM python:3.11-slim

# uv binary (pinned major; see https://docs.astral.sh/uv/guides/integration/docker/)
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Put the project venv on PATH so uvicorn/gunicorn/alembic resolve directly.
    PATH="/app/.venv/bin:$PATH"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (cached layer — only busts when the lock changes)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Download spaCy model for Presidio NER (Named Entity Recognition)
RUN python -m spacy download en_core_web_lg

# Copy application code, then install the project itself
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

EXPOSE 8000

# Production default: gunicorn with uvicorn workers, no auto-reload.
# The dev compose overrides this with `uvicorn --reload` (see docker-compose.yml).
CMD ["gunicorn", "app.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
