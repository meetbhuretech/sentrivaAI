from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "local"
    app_name: str = "SENTINELAI"
    log_level: str = "INFO"
    secret_key: str = "change-me-to-a-long-random-string"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = "postgresql+asyncpg://sentinelai:sentinelai@localhost:5432/sentinelai"
    database_url_sync: str = "postgresql://sentinelai:sentinelai@localhost:5432/sentinelai"
    redis_url: str = "redis://localhost:6379/0"

    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "ChangeMeAdmin123!"
    bootstrap_admin_name: str = "SENTINELAI Admin"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    default_ai_provider: str = "deterministic"
    default_ai_model: str = "rules-v1"

    investigation_timeout_seconds: int = 120
    agent_timeout_seconds: int = 30
    max_tool_calls: int = 40
    max_tokens_per_investigation: int = 80_000
    max_estimated_cost_usd: float = 1.0

    prometheus_url: str = "http://localhost:9090"
    simulator_internal_token: str = "change-me-simulator-token"
    rate_limit_per_minute: int = 120

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors(cls, value: object) -> object:
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                import json

                return json.loads(raw)
            return [part.strip() for part in raw.split(",") if part.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
