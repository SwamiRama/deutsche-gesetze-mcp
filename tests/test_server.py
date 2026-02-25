from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from deutsche_gesetze_mcp.config import Settings
from deutsche_gesetze_mcp.db import Database
from deutsche_gesetze_mcp.parser import parse_law_xml
from deutsche_gesetze_mcp.server import create_server


@pytest.fixture
def mcp_app(tmp_path: Path, sample_bgb_path: Path, sample_gg_path: Path):
    db_path = tmp_path / "test.db"
    cfg = Settings(
        database_path=db_path,
        data_dir=tmp_path,
        auth_token="",
        log_format="console",
        log_level="WARNING",
    )

    db = Database(db_path)
    db.connect()
    db.upsert_law(parse_law_xml(sample_bgb_path, "bgb"))
    db.upsert_law(parse_law_xml(sample_gg_path, "gg"))
    db.close()

    mcp = create_server(cfg)
    return mcp.http_app(path="/mcp", stateless_http=True)


def test_health_endpoint(mcp_app) -> None:
    client = TestClient(mcp_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["law_count"] == 2
    assert data["norm_count"] == 7


def test_health_shows_stats(mcp_app) -> None:
    client = TestClient(mcp_app)
    resp = client.get("/health")
    data = resp.json()
    assert data["law_count"] == 2
    assert data["norm_count"] == 7
    assert data["status"] == "ok"
