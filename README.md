# Deutsche Gesetze MCP Server

MCP server providing German law texts from [gesetze-im-internet.de](https://www.gesetze-im-internet.de/) via Streamable HTTP. Built with FastMCP 3.x and SQLite + FTS5 for full-text search.

## Features

- Browse and search all German federal laws
- Full-text search with FTS5 snippets
- Retrieve individual paragraphs or ranges
- Law structure (table of contents) and metadata
- Bearer token auth, rate limiting, structured logging

## MCP Tools

| Tool | Description |
|---|---|
| `list_laws` | Browse available laws with optional filter |
| `get_paragraph` | Single paragraph by law abbreviation + section identifier |
| `get_paragraphs_range` | Range of consecutive paragraphs |
| `get_law_structure` | Table of contents for a law |
| `search_laws` | FTS5 full-text search with snippets |
| `get_law_metadata` | Law metadata (title, date, norm count) |

## Quickstart

```bash
uv sync --dev                    # Install all deps
uv run update-laws               # Download + index all laws
uv run deutsche-gesetze-mcp      # Start server
```

## Docker

```bash
docker compose up -d
docker exec gesetze-mcp python /app/scripts/update_laws.py
```

## Configuration

All environment variables are prefixed with `GESETZE_`. See [`.env.example`](.env.example) for the full list.

| Variable | Default | Description |
|---|---|---|
| `GESETZE_HOST` | `127.0.0.1` | Listen address |
| `GESETZE_PORT` | `8000` | Listen port |
| `GESETZE_AUTH_TOKEN` | _(empty)_ | Bearer token (disabled if empty) |
| `GESETZE_DATABASE_PATH` | `/data/gesetze.db` | SQLite database path |
| `GESETZE_DATA_DIR` | `/data` | Data directory |
| `GESETZE_DOWNLOAD_CONCURRENCY` | `10` | Parallel downloads |
| `GESETZE_LAW_SLUGS` | _(empty)_ | Comma-separated law slugs to download (all if empty) |
| `GESETZE_LOG_LEVEL` | `INFO` | Log level |
| `GESETZE_LOG_FORMAT` | `json` | Log format (`json` or `console`) |

## Development

```bash
uv run pytest -v                 # Run tests
uv run ruff format src/ tests/   # Format
uv run ruff check src/ tests/    # Lint
uv run mypy src/                 # Type check
```

## Project Structure

- `src/deutsche_gesetze_mcp/server.py` -- FastMCP server, tools, health endpoint, auth
- `src/deutsche_gesetze_mcp/db.py` -- SQLite + FTS5 database layer
- `src/deutsche_gesetze_mcp/parser.py` -- XML parser for gesetze-im-internet.de format
- `src/deutsche_gesetze_mcp/downloader.py` -- Async download of law ZIPs
- `src/deutsche_gesetze_mcp/config.py` -- Pydantic Settings configuration
- `scripts/update_laws.py` -- Standalone download + index script

## Legal / Data Sources

Law texts are sourced from [gesetze-im-internet.de](https://www.gesetze-im-internet.de/), a service provided by the German Federal Ministry of Justice. The texts are made available "zur freien Nutzung und Weiterverwendung" (for free use and redistribution).

German law texts are official works (_amtliche Werke_) under [Section 5(1) UrhG](https://www.gesetze-im-internet.de/urhg/__5.html) and are therefore not subject to copyright.

**Note:** The texts provided by this server are **not the official versions** (_nicht die amtliche Fassung_). The official, legally binding versions are published at [recht.bund.de](https://www.recht.bund.de).

## License

This project is licensed under the [MIT License](LICENSE).
