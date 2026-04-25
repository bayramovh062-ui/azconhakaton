"""Application configuration loaded from `.env` via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Database ----
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://nexusaz:nexusaz@localhost:5432/nexusaz"
    )

    # ---- Auth ----
    SECRET_KEY: str = Field(default="change-me-in-production-please")
    ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24)

    # ---- Geography (Baku commercial port) ----
    BAKU_PORT_LAT: float = Field(default=40.3500)
    BAKU_PORT_LON: float = Field(default=49.8700)

    # ---- Fuel / emission factors ----
    # liters per nautical mile per knot of speed
    FUEL_CONSUMPTION_RATE: float = Field(default=0.12)
    # kg CO2 per liter of marine fuel
    CO2_PER_LITER: float = Field(default=2.68)

    # ---- Background tasks ----
    AIS_TICK_SECONDS: int = Field(default=10)
    JIT_BROADCAST_SECONDS: int = Field(default=5)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
