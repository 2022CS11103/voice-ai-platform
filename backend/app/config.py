from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def _reload_env() -> None:
    load_dotenv(_ENV_FILE, override=True)


_reload_env()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    port: int = 5050
    public_base_url: str = "http://localhost:5050"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "sqlite+aiosqlite:///./voice_ai.db"

    groq_api_key: str = ""
    groq_llm_model: str = "llama-3.3-70b-versatile"
    groq_stt_model: str = "whisper-large-v3-turbo"
    groq_temperature: float = 0.6

    tts_voice: str = "en-US-JennyNeural"

    openai_api_key: str = ""
    openai_voice: str = "alloy"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    demo_email: str = "owner@abcdental.com"
    demo_password: str = "demo1234"
    demo_name: str = "Ananya"

    @field_validator(
        "twilio_account_sid",
        "twilio_auth_token",
        "twilio_phone_number",
        "groq_api_key",
        "public_base_url",
        mode="before",
    )
    @classmethod
    def strip_secrets(cls, v):
        if v is None:
            return ""
        return str(v).strip().strip('"').strip("'")

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def use_pgvector(self) -> bool:
        return "postgresql" in self.database_url

    @property
    def twilio_ready(self) -> bool:
        return bool(
            self.twilio_account_sid.startswith("AC")
            and self.twilio_auth_token
            and self.twilio_phone_number.startswith("+")
        )


@lru_cache
def get_settings() -> Settings:
    _reload_env()
    return Settings()


def refresh_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
