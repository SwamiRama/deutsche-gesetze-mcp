from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from deutsche_gesetze_mcp.config import Settings
from deutsche_gesetze_mcp.db import Database
from deutsche_gesetze_mcp.server import _create_auth_middleware, create_server


@pytest.fixture
def auth_app(tmp_path: Path):
    db_path = tmp_path / "test.db"
    cfg = Settings(
        database_path=db_path,
        data_dir=tmp_path,
        auth_token="test-secret-token",
        log_format="console",
        log_level="WARNING",
    )

    db = Database(db_path)
    db.connect()
    db.close()

    mcp = create_server(cfg)
    app = mcp.http_app(path="/mcp", stateless_http=True)

    middleware_cls = _create_auth_middleware(cfg.auth_token)
    if middleware_cls:
        app.add_middleware(middleware_cls)

    return app


@pytest.fixture
def noauth_app(tmp_path: Path):
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
    db.close()

    mcp = create_server(cfg)
    return mcp.http_app(path="/mcp", stateless_http=True)


def test_health_no_auth_required(auth_app) -> None:
    client = TestClient(auth_app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_mcp_requires_auth(auth_app) -> None:
    client = TestClient(auth_app)
    resp = client.post("/mcp")
    assert resp.status_code == 401


def test_mcp_wrong_token(auth_app) -> None:
    client = TestClient(auth_app)
    resp = client.post("/mcp", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401


def test_mcp_missing_bearer_prefix(auth_app) -> None:
    client = TestClient(auth_app)
    resp = client.post("/mcp", headers={"Authorization": "Token test-secret-token"})
    assert resp.status_code == 401


def test_health_without_auth_config(noauth_app) -> None:
    client = TestClient(noauth_app)
    resp = client.get("/health")
    assert resp.status_code == 200
