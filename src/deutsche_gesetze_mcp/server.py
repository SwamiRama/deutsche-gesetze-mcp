from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

import structlog
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from starlette.requests import Request
from starlette.responses import JSONResponse

from deutsche_gesetze_mcp.config import Settings, settings
from deutsche_gesetze_mcp.db import Database
from deutsche_gesetze_mcp.log_config import setup_logging

logger = structlog.get_logger()


class _RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        timestamps = self._requests[key]
        self._requests[key] = [t for t in timestamps if t > cutoff]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True


def _create_auth_middleware(token: str) -> Any:
    if not token:
        return None

    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response

    class BearerAuthMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Response:
            if request.url.path == "/health":
                return await call_next(request)

            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Bearer "):
                return JSONResponse({"error": "Missing or invalid Authorization header"}, status_code=401)

            provided_token = auth_header[7:]
            if provided_token != token:
                return JSONResponse({"error": "Invalid token"}, status_code=401)

            return await call_next(request)

    return BearerAuthMiddleware


def _create_rate_limit_middleware(max_requests: int, window_minutes: int) -> Any:
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response

    limiter = _RateLimiter(max_requests, window_minutes * 60)

    class RateLimitMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: Any) -> Response:
            if request.url.path == "/health":
                return await call_next(request)

            client_ip = request.client.host if request.client else "unknown"
            if not limiter.is_allowed(client_ip):
                return JSONResponse({"error": "Rate limit exceeded"}, status_code=429)

            return await call_next(request)

    return RateLimitMiddleware


def create_server(cfg: Settings | None = None) -> FastMCP:
    cfg = cfg or settings
    setup_logging(cfg.log_level, cfg.log_format)

    mcp = FastMCP("deutsche-gesetze-mcp")

    db = Database(cfg.database_path)
    db.connect()

    # Store config on the server instance for get_app() to access
    mcp._cfg = cfg  # type: ignore[attr-defined]

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        stats = db.get_stats()
        return JSONResponse({"status": "ok", **stats})

    @mcp.tool(
        description=(
            "List available German laws in the database. "
            "Use the optional filter parameter to search by abbreviation (e.g. 'BGB') or title. "
            "Returns jurabk (abbreviation), full_title, and norm_count."
        ),
    )
    def list_laws(filter: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:  # noqa: A002
        return db.list_laws(filter_text=filter, limit=min(limit, 200), offset=offset)

    @mcp.tool(
        description=(
            "Get a single paragraph/article from a German law. "
            "Parameters: jurabk = law abbreviation (e.g. 'BGB'), enbez = paragraph identifier (e.g. '§ 823'). "
            "Note: enbez must include the § or Art prefix with a space."
        ),
    )
    def get_paragraph(jurabk: str, enbez: str) -> dict:
        result = db.get_paragraph(jurabk, enbez)
        if not result:
            raise ToolError(
                f"Paragraph '{enbez}' not found in '{jurabk}'. "
                f"Use get_law_structure to see available paragraphs, "
                f"or list_laws to check the law abbreviation."
            )
        return result

    @mcp.tool(
        description=(
            "Get a range of consecutive paragraphs from a German law. "
            "Parameters: jurabk = law abbreviation, start = first paragraph (e.g. '§ 823'), "
            "end = last paragraph (e.g. '§ 826'). Returns up to 50 paragraphs in document order."
        ),
    )
    def get_paragraphs_range(jurabk: str, start: str, end: str) -> list[dict]:
        results = db.get_paragraphs_range(jurabk, start, end)
        if not results:
            raise ToolError(
                f"No paragraphs found between '{start}' and '{end}' in '{jurabk}'. "
                f"Check the exact enbez values using get_law_structure."
            )
        return results

    @mcp.tool(
        description=(
            "Get the table of contents / structure of a German law. "
            "Returns all paragraphs with their enbez, titel, and section hierarchy (gliederung). "
            "Useful for navigating large laws like BGB or StGB."
        ),
    )
    def get_law_structure(jurabk: str) -> list[dict]:
        results = db.get_law_structure(jurabk)
        if not results:
            raise ToolError(f"Law '{jurabk}' not found. Use list_laws to find the correct abbreviation.")
        return results

    @mcp.tool(
        description=(
            "Full-text search across German law texts. "
            "Use singular forms for best results (e.g. 'Kuendigung' not 'Kuendigungen'). "
            "Optional: restrict to specific laws with the laws parameter (list of jurabk). "
            "Returns matching paragraphs with text snippets showing context around matches."
        ),
    )
    def search_laws(query: str, laws: list[str] | None = None, limit: int = 20, offset: int = 0) -> list[dict]:
        results = db.search(query, laws=laws, limit=min(limit, 100), offset=offset)
        if not results:
            raise ToolError(
                f"No results for '{query}'. Try shorter or singular search terms. "
                f"FTS does not support stemming, so use the exact word form."
            )
        return results

    @mcp.tool(
        description=(
            "Get metadata for a specific German law. "
            "Returns full title, enactment date, slug, and total number of norms/paragraphs."
        ),
    )
    def get_law_metadata(jurabk: str) -> dict:
        result = db.get_law_metadata(jurabk)
        if not result:
            raise ToolError(f"Law '{jurabk}' not found. Use list_laws to find the correct abbreviation.")
        return result

    return mcp


def get_app():
    mcp = create_server()
    cfg: Settings = mcp._cfg  # type: ignore[attr-defined]
    app = mcp.http_app(path="/mcp", stateless_http=True)

    app.add_middleware(_create_rate_limit_middleware(cfg.rate_limit_requests, cfg.rate_limit_window_minutes))

    if cfg.auth_token:
        middleware_cls = _create_auth_middleware(cfg.auth_token)
        if middleware_cls:
            app.add_middleware(middleware_cls)

    return app


def main() -> None:
    import uvicorn

    setup_logging(settings.log_level, settings.log_format)
    uvicorn.run(
        "deutsche_gesetze_mcp.server:get_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        workers=1,
    )


if __name__ == "__main__":
    main()
