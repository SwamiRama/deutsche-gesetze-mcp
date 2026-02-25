from __future__ import annotations

from pathlib import Path

import pytest

from deutsche_gesetze_mcp.db import Database
from deutsche_gesetze_mcp.parser import parse_law_xml

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def sample_bgb_path() -> Path:
    return FIXTURES_DIR / "sample_bgb.xml"


@pytest.fixture
def sample_gg_path() -> Path:
    return FIXTURES_DIR / "sample_gg.xml"


@pytest.fixture
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "test.db")
    database.connect()
    yield database  # type: ignore[misc]
    database.close()


@pytest.fixture
def populated_db(db: Database, sample_bgb_path: Path, sample_gg_path: Path) -> Database:
    bgb = parse_law_xml(sample_bgb_path, "bgb")
    gg = parse_law_xml(sample_gg_path, "gg")
    db.upsert_law(bgb)
    db.upsert_law(gg)
    return db
