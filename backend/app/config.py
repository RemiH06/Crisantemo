"""Configuración del backend, leída de variables de entorno (ver .env.example)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_path: str = "/app/models/crisantemo_v1.joblib"
    feature_schema_path: str = "/app/models/feature_schema_v1.json"
    cors_origins: str = "http://localhost:9000"
    log_level: str = "info"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
