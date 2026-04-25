"""NexusAZ FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from backend.ais.simulator import simulator
from backend.alerts.router import router as alerts_router
from backend.auth.router import router as auth_router
from backend.bookings.router import router as bookings_router
from backend.captain.router import router as captain_router
from backend.config import settings
from backend.database import AsyncSessionLocal, close_engine
from backend.esg.router import router as esg_router
from backend.jit.router import compute_fleet_status, router as jit_router
from backend.owner.router import router as owner_router
from backend.stats.router import router as stats_router
from backend.vessels.router import router as vessels_router
from backend.websocket.manager import manager

logger = logging.getLogger("azmarine")
logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

async def _ais_tick_loop() -> None:
    """Persist mock AIS data every AIS_TICK_SECONDS."""
    while True:
        try:
            async with AsyncSessionLocal() as session:
                count = await simulator.persist_tick(session)
                logger.debug("AIS tick: persisted %d positions", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("AIS tick failed")
        await asyncio.sleep(settings.AIS_TICK_SECONDS)


async def _jit_broadcast_loop() -> None:
    """Compute fleet status and broadcast to WS clients every N seconds."""
    while True:
        try:
            if manager.active_connections:
                async with AsyncSessionLocal() as session:
                    fleet = await compute_fleet_status(session)
                payload = {
                    "type": "fleet_status",
                    "vessels": [v.model_dump(mode="json") for v in fleet],
                }
                await manager.broadcast(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("JIT broadcast failed")
        await asyncio.sleep(settings.JIT_BROADCAST_SECONDS)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    enable_sim = (
        os.getenv("AZMARINE_ENABLE_AIS_SIM")
        or os.getenv("NEXUSAZ_ENABLE_AIS_SIM", "true")
    ).lower() != "false"
    tasks: list[asyncio.Task] = []
    if enable_sim:
        tasks.append(asyncio.create_task(_ais_tick_loop(), name="ais-tick"))
    tasks.append(asyncio.create_task(_jit_broadcast_loop(), name="jit-broadcast"))
    logger.info("AZMarine background tasks started: %s", [t.get_name() for t in tasks])
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await close_engine()
        logger.info("AZMarine shutdown complete")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AZMarine API",
    version="2.0.0",
    description="AZMarine — Just-in-Time vessel arrival intelligence platform for the Caspian.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # development; tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(vessels_router)
app.include_router(bookings_router)
app.include_router(jit_router)
app.include_router(esg_router)
app.include_router(alerts_router)
app.include_router(stats_router)
app.include_router(owner_router)
app.include_router(captain_router)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/", tags=["health"])
async def root() -> dict:
    return {
        "service": "AZMarine",
        "version": "2.0.0",
        "status": "ok",
        "port": "Baku International Sea Trade Port",
    }


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "healthy"}


# ---------------------------------------------------------------------------
# WebSocket: /ws/fleet
# ---------------------------------------------------------------------------

@app.websocket("/ws/fleet")
async def ws_fleet(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    # Send an initial snapshot immediately so the dashboard isn't blank
    try:
        async with AsyncSessionLocal() as session:
            fleet = await compute_fleet_status(session)
        await websocket.send_json(
            {
                "type": "fleet_status",
                "vessels": [v.model_dump(mode="json") for v in fleet],
            }
        )
    except Exception:
        logger.exception("Initial WS snapshot failed")

    try:
        while True:
            # We don't expect inbound messages, but keep the loop alive.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WebSocket error")
    finally:
        await manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
