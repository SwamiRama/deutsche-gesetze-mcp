from __future__ import annotations

import asyncio
import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import structlog
from lxml import etree

from deutsche_gesetze_mcp.models import LawEntry

logger = structlog.get_logger()

TOC_URL = "https://www.gesetze-im-internet.de/gii-toc.xml"


async def fetch_toc(client: httpx.AsyncClient) -> list[LawEntry]:
    resp = await client.get(TOC_URL)
    resp.raise_for_status()

    root = etree.fromstring(resp.content)  # noqa: S320
    entries: list[LawEntry] = []

    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        if not link:
            continue
        slug = link.rstrip("/").split("/")[-1]
        entries.append(LawEntry(slug=slug, title=title, url=link))

    logger.info("toc_fetched", count=len(entries))
    return entries


async def download_law_zip(
    client: httpx.AsyncClient,
    entry: LawEntry,
    xml_dir: Path,
    semaphore: asyncio.Semaphore,
) -> Path | None:
    async with semaphore:
        url = f"https://www.gesetze-im-internet.de/{entry.slug}/xml.zip"
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.warning("download_failed", slug=entry.slug, status=e.response.status_code)
            return None
        except httpx.RequestError as e:
            logger.warning("download_error", slug=entry.slug, error=str(e))
            return None

        try:
            with zipfile.ZipFile(BytesIO(resp.content)) as zf:
                xml_files = [n for n in zf.namelist() if n.endswith(".xml")]
                if not xml_files:
                    logger.warning("no_xml_in_zip", slug=entry.slug)
                    return None
                xml_content = zf.read(xml_files[0])
        except zipfile.BadZipFile:
            logger.warning("bad_zip", slug=entry.slug)
            return None

        out_path = xml_dir / f"{entry.slug}.xml"
        out_path.write_bytes(xml_content)
        return out_path


async def download_all(
    data_dir: Path,
    concurrency: int = 10,
    slugs: list[str] | None = None,
) -> list[Path]:
    xml_dir = data_dir / "xml"
    xml_dir.mkdir(parents=True, exist_ok=True)

    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0), follow_redirects=True) as client:
        entries = await fetch_toc(client)

        if slugs:
            slug_set = set(slugs)
            entries = [e for e in entries if e.slug in slug_set]
            logger.info("filtered_entries", count=len(entries))

        tasks = [download_law_zip(client, entry, xml_dir, semaphore) for entry in entries]
        results = await asyncio.gather(*tasks)

    paths = [p for p in results if p is not None]
    logger.info("download_complete", total=len(entries), success=len(paths))
    return paths
