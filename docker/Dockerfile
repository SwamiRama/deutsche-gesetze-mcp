FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build
ENV UV_PYTHON_PREFERENCE=only-system
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --frozen --no-install-project 2>/dev/null || uv sync --no-dev --no-install-project

COPY src/ src/
COPY scripts/ scripts/
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Download all laws and build the SQLite database at build time
ENV PATH="/build/.venv/bin:$PATH" PYTHONPATH="/build/src"
ENV GESETZE_DATABASE_PATH=/build/gesetze.db GESETZE_DATA_DIR=/build/data
RUN python scripts/update_laws.py


FROM python:3.12-slim AS production

RUN groupadd -g 1001 mcp && useradd -u 1001 -g mcp -m -s /bin/sh mcp

COPY --from=builder --chown=mcp:mcp /build/.venv /app/.venv
COPY --from=builder --chown=mcp:mcp /build/src /app/src
COPY --from=builder --chown=mcp:mcp /build/scripts /app/scripts
COPY --from=builder --chown=mcp:mcp /build/gesetze.db /app/gesetze.db
COPY --chown=mcp:mcp docker/entrypoint.sh /app/entrypoint.sh

RUN mkdir -p /data /tmp && chown mcp:mcp /data /tmp

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    GESETZE_HOST=0.0.0.0 \
    GESETZE_DATABASE_PATH=/tmp/gesetze.db \
    GESETZE_DATA_DIR=/data

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

USER mcp
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "deutsche_gesetze_mcp.server:get_app", "--factory", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
