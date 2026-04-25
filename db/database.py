"""NexusAZ — async database infrastructure.

Provides:
    * `engine`       — SQLAlchemy AsyncEngine (asyncpg driver)
    * `AsyncSessionLocal` — async sessionmaker
    * `Base`         — declarative base shared by all ORM models
    * `get_session`  — FastAPI/Starlette-style async dependency
    * `init_models`  — utility to create all tables (dev only)
    * `close_engine` — graceful shutdown helper
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

DEFAULT_DATABASE_URL = (
    "postgresql+asyncpg://nexusaz:nexusaz@localhost:5432/nexusaz"
)

DATABASE_URL: str = os.getenv("NEXUSAZ_DATABASE_URL", DEFAULT_DATABASE_URL)

DB_ECHO: bool = os.getenv("NEXUSAZ_DB_ECHO", "false").lower() == "true"
DB_POOL_SIZE: int = int(os.getenv("NEXUSAZ_DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW: int = int(os.getenv("NEXUSAZ_DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT: int = int(os.getenv("NEXUSAZ_DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE: int = int(os.getenv("NEXUSAZ_DB_POOL_RECYCLE", "1800"))


# ---------------------------------------------------------------------------
# Engine & session factory
# ---------------------------------------------------------------------------

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    future=True,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    pool_pre_ping=True,
)

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
    """Shared declarative base for all NexusAZ ORM models."""
    pass


# ---------------------------------------------------------------------------
# Dependency-ready async session generator
# ---------------------------------------------------------------------------

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional async session.

    Usage (FastAPI):
        @app.get("/vessels")
        async def list_vessels(session: AsyncSession = Depends(get_session)):
            ...
    """
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
    """Create all tables (development convenience only).

    In production, schema management must go through Alembic migrations.
    """
    # Local import to avoid circular dependency with models.py
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_engine() -> None:
    """Dispose of the engine on application shutdown."""
    await engine.dispose()
