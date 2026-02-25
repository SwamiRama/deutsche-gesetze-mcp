# Deutsche Gesetze MCP Server

MCP server providing German law texts from gesetze-im-internet.de via Streamable HTTP.

## Quick Reference

- **Language:** Python 3.12, managed with `uv`
- **Framework:** FastMCP 3.x (standalone)
- **Database:** SQLite + FTS5
- **Data source:** gesetze-im-internet.de (XML format)

## Commands

```bash
uv sync --dev                    # Install all deps
uv run pytest -v                 # Run tests
uv run ruff format src/ tests/   # Format
uv run ruff check src/ tests/    # Lint
uv run mypy src/                 # Type check
uv run deutsche-gesetze-mcp      # Start server
uv run update-laws               # Download + index all laws
```

## Project Structure

- `src/deutsche_gesetze_mcp/server.py` - FastMCP server, 6 tools, health endpoint, auth
- `src/deutsche_gesetze_mcp/db.py` - SQLite + FTS5 database layer
- `src/deutsche_gesetze_mcp/parser.py` - XML parser for gesetze-im-internet.de format
- `src/deutsche_gesetze_mcp/downloader.py` - Async download of law ZIPs
- `src/deutsche_gesetze_mcp/config.py` - Pydantic Settings (GESETZE_ env prefix)
- `scripts/update_laws.py` - Standalone download + index script

## MCP Tools

1. `list_laws` - Browse available laws with optional filter
2. `get_paragraph` - Single paragraph by jurabk + enbez
3. `get_paragraphs_range` - Range of consecutive paragraphs
4. `get_law_structure` - Table of contents for a law
5. `search_laws` - FTS5 full-text search with snippets
6. `get_law_metadata` - Law metadata (title, date, norm count)

## Config (ENV)

All prefixed with `GESETZE_`. See `.env.example` for full list.

## Docker

```bash
docker compose up -d
docker exec gesetze-mcp python /app/scripts/update_laws.py
```
