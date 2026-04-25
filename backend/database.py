"""Async database layer for the NexusAZ backend.

Defaults to a local async SQLite file so the app runs on any machine
without PostgreSQL/PostGIS. Override `DATABASE_URL` (or
`NEXUSAZ_DATABASE_URL`) in `.env` to point at a real Postgres+PostGIS
deployment if desired — but in that case prefer the canonical models
in `db/models.py`.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./nexusaz.db"

DATABASE_URL: str = (
    os.getenv("AZMARINE_DATABASE_URL")
    or os.getenv("NEXUSAZ_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or DEFAULT_DATABASE_URL
)

DB_ECHO: bool = (
    os.getenv("AZMARINE_DB_ECHO")
    or os.getenv("NEXUSAZ_DB_ECHO", "false")
).lower() == "true"

_is_sqlite = DATABASE_URL.startswith("sqlite")


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

_engine_kwargs: dict = {"echo": DB_ECHO, "future": True}

if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=int(os.getenv("NEXUSAZ_DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("NEXUSAZ_DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("NEXUSAZ_DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("NEXUSAZ_DB_POOL_RECYCLE", "1800")),
        pool_pre_ping=True,
    )

engine: AsyncEngine = create_async_engine(DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Shared declarative base for all NexusAZ backend ORM models."""
    pass


# ---------------------------------------------------------------------------
# Dependency-ready async session generator
# ---------------------------------------------------------------------------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------

async def init_models() -> None:
    """Create all tables (development convenience)."""
    from backend import models  # noqa: F401  -- ensure models register on Base

    async with engine.begin() as conn:
        if _is_sqlite:
            from sqlalchemy import text
            await conn.execute(text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)


async def reset_models() -> None:
    """Drop *and* re-create every table — used by bootstrap when the schema
    changes (e.g. new columns). Destroys all data."""
    from backend import models  # noqa: F401

    async with engine.begin() as conn:
        if _is_sqlite:
            from sqlalchemy import text
            await conn.execute(text("PRAGMA foreign_keys=OFF"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        if _is_sqlite:
            from sqlalchemy import text
            await conn.execute(text("PRAGMA foreign_keys=ON"))


async def close_engine() -> None:
    await engine.dispose()


__all__ = [
    "AsyncSessionLocal",
    "Base",
    "DATABASE_URL",
    "close_engine",
    "engine",
    "get_session",
    "init_models",
]
