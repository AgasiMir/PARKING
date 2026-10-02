from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: Literal["LOCAL", "TEST", "DEV", "PROD"] = "LOCAL"

    DB_DRIVER: str = "postgresql+asyncpg"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: SecretStr = SecretStr("postgres")
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    POSTGRES_DB: str = "cursor_offset"

    @property
    def DB_URL(self) -> str:
        return (
            f"{self.DB_DRIVER}://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD.get_secret_value()}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.POSTGRES_DB}"
        )

    model_config = SettingsConfigDict(env_file=[".env.local"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
