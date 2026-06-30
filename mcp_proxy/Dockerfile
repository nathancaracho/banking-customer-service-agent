FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app/mcp_proxy

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY observability /app/observability
COPY mcp_proxy/pyproject.toml mcp_proxy/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY mcp_proxy/mcp_proxy ./mcp_proxy

CMD ["uv", "run", "--no-sync", "python", "-m", "mcp_proxy.main"]
