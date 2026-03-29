"""
services/config.py

Loads and validates environment configuration.
Fails fast with a clear message if required variables are missing.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel, field_validator

load_dotenv()


class Config(BaseModel):
    telegram_bot_token: str
    google_sheets_spreadsheet_id: Optional[str] = None  # Optional — blank = mock mode
    google_application_credentials: str
    anthropic_api_key: Optional[str] = None  # Optional: falls back to template responses
    app_env: str = "dev"
    log_level: str = "INFO"

    @field_validator("telegram_bot_token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("TELEGRAM_BOT_TOKEN is required and cannot be empty.")
        return v

    @property
    def is_dev(self) -> bool:
        return self.app_env.lower() == "dev"

    @property
    def claude_enabled(self) -> bool:
        return bool(self.anthropic_api_key and self.anthropic_api_key.strip())


def load_config() -> Config:
    """Load config from environment. Raises ValueError on missing required fields."""
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        raise EnvironmentError(
            "TELEGRAM_BOT_TOKEN is required.\n"
            "Copy .env.example to .env and fill in the value."
        )

    return Config(
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        google_sheets_spreadsheet_id=os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID") or None,
        google_application_credentials=os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS",
            "/app/credentials/service-account.json",
        ),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        app_env=os.getenv("APP_ENV", "dev"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
