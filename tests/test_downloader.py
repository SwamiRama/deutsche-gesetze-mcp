from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import httpx
import pytest
import respx

from deutsche_gesetze_mcp.downloader import download_all, fetch_toc


@pytest.fixture
def toc_xml() -> bytes:
    return Path(__file__).parent.joinpath("fixtures", "sample_toc.xml").read_bytes()


@pytest.fixture
def sample_zip() -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        xml_content = (
            '<?xml version="1.0"?><dokumente><norm><metadaten>'
            "<jurabk>BGB</jurabk><langue>Test</langue>"
            "</metadaten><textdaten/></norm></dokumente>"
        )
        zf.writestr("bgb.xml", xml_content)
    return buf.getvalue()


@respx.mock
async def test_fetch_toc(toc_xml: bytes) -> None:
    respx.get("https://www.gesetze-im-internet.de/gii-toc.xml").mock(return_value=httpx.Response(200, content=toc_xml))
    async with httpx.AsyncClient() as client:
        entries = await fetch_toc(client)

    assert len(entries) == 3
    assert entries[0].slug == "bgb"
    assert entries[0].title == "Bürgerliches Gesetzbuch"
    assert entries[1].slug == "gg"
    assert entries[2].slug == "stgb"


@respx.mock
async def test_download_all(tmp_path: Path, toc_xml: bytes, sample_zip: bytes) -> None:
    respx.get("https://www.gesetze-im-internet.de/gii-toc.xml").mock(return_value=httpx.Response(200, content=toc_xml))
    respx.get("https://www.gesetze-im-internet.de/bgb/xml.zip").mock(
        return_value=httpx.Response(200, content=sample_zip)
    )
    respx.get("https://www.gesetze-im-internet.de/gg/xml.zip").mock(return_value=httpx.Response(404))
    respx.get("https://www.gesetze-im-internet.de/stgb/xml.zip").mock(
        return_value=httpx.Response(200, content=sample_zip)
    )

    paths = await download_all(tmp_path, concurrency=2, slugs=["bgb", "gg", "stgb"])
    assert len(paths) == 2  # gg failed (404)
    assert (tmp_path / "xml" / "bgb.xml").exists()
    assert not (tmp_path / "xml" / "gg.xml").exists()
    assert (tmp_path / "xml" / "stgb.xml").exists()


@respx.mock
async def test_download_all_with_slug_filter(tmp_path: Path, toc_xml: bytes, sample_zip: bytes) -> None:
    respx.get("https://www.gesetze-im-internet.de/gii-toc.xml").mock(return_value=httpx.Response(200, content=toc_xml))
    respx.get("https://www.gesetze-im-internet.de/bgb/xml.zip").mock(
        return_value=httpx.Response(200, content=sample_zip)
    )

    paths = await download_all(tmp_path, concurrency=2, slugs=["bgb"])
    assert len(paths) == 1
