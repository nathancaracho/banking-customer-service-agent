FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/agents

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY observability /app/observability
COPY agents/pyproject.toml agents/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY agents/alembic.ini ./
COPY agents/migrations ./migrations
COPY agents/agents ./agents
COPY agents/main.py ./

CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && exec uv run --no-sync python main.py"]
