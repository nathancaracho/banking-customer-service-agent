FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/identity

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY observability /app/observability
COPY identity/pyproject.toml identity/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY identity/alembic.ini ./
COPY identity/migrations ./migrations
COPY identity/identity ./identity

CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && exec uv run --no-sync uvicorn identity.main:app --host 0.0.0.0 --port 8100"]
