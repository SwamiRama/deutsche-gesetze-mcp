from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "GESETZE_"}

    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False

    auth_token: str = ""

    database_path: Path = Path("/data/gesetze.db")
    data_dir: Path = Path("/data")

    rate_limit_requests: int = 100
    rate_limit_window_minutes: int = 1

    download_concurrency: int = 10
    law_slugs: list[str] | None = None

    log_level: str = "INFO"
    log_format: str = "json"

    @field_validator("law_slugs", mode="before")
    @classmethod
    def parse_law_slugs(cls, v: str | list[str] | None) -> list[str] | None:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            import json

            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return [str(s) for s in parsed]
            except json.JSONDecodeError:
                return [s.strip() for s in v.split(",") if s.strip()]
        return v

    @property
    def xml_dir(self) -> Path:
        return self.data_dir / "xml"


settings = Settings()
