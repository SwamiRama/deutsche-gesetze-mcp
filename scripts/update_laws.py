from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

from deutsche_gesetze_mcp.config import settings
from deutsche_gesetze_mcp.db import Database
from deutsche_gesetze_mcp.downloader import download_all
from deutsche_gesetze_mcp.log_config import setup_logging
from deutsche_gesetze_mcp.parser import parse_law_xml

logger = structlog.get_logger()


async def update(data_dir: Path, db_path: Path, concurrency: int, slugs: list[str] | None) -> None:
    setup_logging(settings.log_level, settings.log_format)

    logger.info("starting_download", data_dir=str(data_dir), concurrency=concurrency)
    xml_paths = await download_all(data_dir, concurrency=concurrency, slugs=slugs)

    db = Database(db_path)
    db.connect()

    success = 0
    errors = 0

    for xml_path in xml_paths:
        slug = xml_path.stem
        try:
            law = parse_law_xml(xml_path, slug)
            if law.jurabk:
                db.upsert_law(law)
                success += 1
            else:
                logger.warning("empty_law", slug=slug)
                errors += 1
        except Exception:
            logger.exception("parse_error", slug=slug)
            errors += 1

    db.close()
    logger.info("update_complete", success=success, errors=errors)


def main() -> None:
    asyncio.run(
        update(
            data_dir=settings.data_dir,
            db_path=settings.database_path,
            concurrency=settings.download_concurrency,
            slugs=settings.law_slugs,
        )
    )


if __name__ == "__main__":
    main()
