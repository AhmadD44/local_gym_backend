from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    debug: bool = False
    app_name: str = "Gym Management System"
    api_prefix: str = "/api/v1"

    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 5
    database_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"

    jwt_algorithm: str = "RS256"
    jwt_private_key_path: str = "./secrets/jwt_private.pem"
    jwt_public_key_path: str = "./secrets/jwt_public.pem"
    jwt_issuer: str = "gym-backend"
    jwt_audience: str = "gym-mobile-app"
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 14

    cors_origins: str = ""

    rate_limit_login_per_minute: int = 5
    rate_limit_register_per_minute: int = 3
    rate_limit_default_per_minute: int = 120

    storage_backend: str = "local"
    storage_local_dir: str = "./uploads"
    storage_bucket: str = "gym-uploads"
    storage_endpoint: str = ""
    storage_region: str = "us-east-1"
    storage_access_key: str = ""
    storage_secret_key: str = ""
    storage_public_base_url: str = "http://localhost:8000/uploads"

    bootstrap_admin_email: str = "admin@example.com"
    bootstrap_admin_password: str = "ChangeMe!12345"

    push_provider: str = "none"
    fcm_service_account_json: str = ""

    @field_validator("cors_origins")
    @classmethod
    def _noop(cls, v: str) -> str:
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def jwt_private_key(self) -> str:
        return Path(self.jwt_private_key_path).read_text()

    @property
    def jwt_public_key(self) -> str:
        return Path(self.jwt_public_key_path).read_text()

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
