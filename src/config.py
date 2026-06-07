"""
STEWARD configuration — loaded from .env via Pydantic Settings.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Anthropic
    anthropic_api_key: Optional[str] = None
    extraction_model: str = "claude-haiku-4-5-20251001"
    query_model: str = "claude-sonnet-4-6"

    # Paths
    docs_dir: Path = PROJECT_ROOT / "docs"
    db_path: Path = PROJECT_ROOT / "steward.db"

    # Email ingestion (optional — requires Gmail App Password)
    steward_email: Optional[str] = None
    steward_email_password: Optional[str] = None   # Gmail App Password (not account password)
    email_poll_minutes: int = 5
    email_imap_host: str = "imap.gmail.com"
    email_imap_port: int = 993

    # Logging
    log_level: str = "INFO"

    @property
    def has_api_key(self) -> bool:
        return bool(self.anthropic_api_key)

    def configure_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s %(name)s %(levelname)s %(message)s",
        )


settings = Settings()
