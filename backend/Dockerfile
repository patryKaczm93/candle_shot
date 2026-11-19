# API image for production (docker-compose.prod.yml). Reached only through Caddy.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Dependencies first, so code changes do not reinstall them. No dev tools (pytest, ruff).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY alembic.ini seed.py ./
COPY migrations ./migrations
COPY app ./app

RUN useradd --system --uid 1000 --no-create-home shop && chown -R shop /app
USER shop

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

# --proxy-headers: client IP and https come from Caddy, the only thing that can reach this port.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
