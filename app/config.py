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
    DB_PORT: int = 6432
    POSTGRES_DB: str = "parking"

    REPLICATION_USER: str = "replicator"
    REPLICATION_PASSWORD: SecretStr = SecretStr("replicator_change_me")

    DB_REPLICA_DRIVER: str = "postgresql+asyncpg"
    POSTGRES_REPLICA_USER: str = "postgres_r"
    POSTGRES_REPLICA_PASSWORD: SecretStr = SecretStr("postgres")
    DB_REPLICA_HOST: str = "localhost"
    DB_REPLICA_PORT: int = 7432
    POSTGRES_REPLICA_DB: str = "parking_r"

    GF_SECURITY_ADMIN_USER: str = "admin"
    GF_SECURITY_ADMIN_PASSWORD: SecretStr = SecretStr("postgres")

    @property
    def DB_URL(self) -> str:
        return (
            f"{self.DB_DRIVER}://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD.get_secret_value()}@{self.DB_HOST}:"
            f"{self.DB_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DB_REPLICA_URL(self) -> str:
        return (
            f"{self.DB_REPLICA_DRIVER}://{self.POSTGRES_REPLICA_USER}:"
            f"{self.POSTGRES_REPLICA_PASSWORD.get_secret_value()}@{self.DB_REPLICA_HOST}:"
            f"{self.DB_REPLICA_PORT}/{self.POSTGRES_REPLICA_DB}"
        )

    model_config = SettingsConfigDict(env_file=[".env.prod", ".env.local"])


@lru_cache
def get_settings() -> Settings:
    return Settings()
