"""JIT recommendation REST router."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.utils import get_current_user
from backend.config import settings
from backend.database import get_session
from backend.models import (
    JitRecommendation,
    PortBooking,
    User,
    Vessel,
    VesselPosition,
)

from .engine import jit_engine

router = APIRouter(prefix="/jit", tags=["jit"])


# Approx marine fuel density (HFO/MGO mix): 0.85 kg/L → t = liters * 0.85 / 1000
LITERS_TO_TONNES = 0.00085


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class JITCalculateRequest(BaseModel):
    vessel_id: uuid.UUID
    booking_id: Optional[uuid.UUID] = None


class JITRecommendationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vessel_id: uuid.UUID
    booking_id: Optional[uuid.UUID] = None
    distance_nm: Optional[float] = None
    time_available_hours: Optional[float] = None
    recommended_speed: float
    current_speed: Optional[float] = None
    status: str
    fuel_saved_liters: Optional[float] = None
    co2_saved_kg: Optional[float] = None
    issued_at: datetime


class FleetVesselStatus(BaseModel):
    vessel_id: uuid.UUID
    vessel_name: str
    booking_id: Optional[uuid.UUID] = None
    lat: float
    lon: float
    current_speed: float
    recommended_speed: float
    distance_nm: float
    time_available_hours: float
    status: str
    fuel_saved_liters: float
    co2_saved_kg: float
    scheduled_arrival: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rationale(result: dict[str, Any]) -> str:
    return (
        f"distance_nm={result['distance_nm']}; "
        f"time_available_hours={result['time_available_hours']}; "
        f"current_speed={result['current_speed']}; "
        f"recommended_speed={result['recommended_speed']}; "
        f"fuel_saved_liters={result['fuel_saved_liters']}; "
        f"co2_saved_kg={result['co2_saved_kg']}"
    )


def _persist_recommendation(
    session: AsyncSession,
    *,
    vessel_id: uuid.UUID,
    booking_id: Optional[uuid.UUID],
    result: dict[str, Any],
    scheduled_arrival: datetime,
) -> JitRecommendation:
    rec = JitRecommendation(
        vessel_id=vessel_id,
        booking_id=booking_id,
        recommended_speed=Decimal(str(result["recommended_speed"])),
        recommended_eta=scheduled_arrival,
        fuel_savings_t=Decimal(
            str(round(result["fuel_saved_liters"] * LITERS_TO_TONNES, 3))
        ),
        co2_savings_kg=Decimal(str(result["co2_saved_kg"])),
        confidence=Decimal("0.9"),
        rationale=_rationale(result),
        status=result["status"],
    )
    session.add(rec)
    return rec


def _rec_to_out(rec: JitRecommendation) -> JITRecommendationOut:
    parsed = _parse_rationale(rec.rationale or "")
    return JITRecommendationOut(
        id=rec.id,
        vessel_id=rec.vessel_id,
        booking_id=rec.booking_id,
        distance_nm=parsed.get("distance_nm"),
        time_available_hours=parsed.get("time_available_hours"),
        recommended_speed=float(rec.recommended_speed),
        current_speed=parsed.get("current_speed"),
        status=rec.status,
        fuel_saved_liters=parsed.get("fuel_saved_liters"),
        co2_saved_kg=float(rec.co2_savings_kg) if rec.co2_savings_kg is not None else None,
        issued_at=rec.issued_at,
    )


def _parse_rationale(rationale: str) -> dict[str, float]:
    """Parse the structured rationale string back into a dict."""
    out: dict[str, float] = {}
    for chunk in rationale.split(";"):
        if "=" not in chunk:
            continue
        k, v = chunk.split("=", 1)
        try:
            out[k.strip()] = float(v.strip())
        except ValueError:
            pass
    return out


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/calculate", response_model=JITRecommendationOut)
async def calculate(
    payload: JITCalculateRequest,
    session: AsyncSession = Depends(get_session),
    _current: User = Depends(get_current_user),
) -> JITRecommendationOut:
    vessel = await session.get(Vessel, payload.vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")

    # Latest known position
    pos = (
        await session.execute(
            select(VesselPosition)
            .where(VesselPosition.vessel_id == payload.vessel_id)
            .order_by(desc(VesselPosition.recorded_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if not pos:
        raise HTTPException(
            status_code=409,
            detail="Vessel has no AIS position yet — cannot compute JIT",
        )

    scheduled_arrival: Optional[datetime] = None
    booking: Optional[PortBooking] = None
    if payload.booking_id:
        booking = await session.get(PortBooking, payload.booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")
        scheduled_arrival = booking.eta
    if scheduled_arrival is None:
        # No booking provided → assume berth slot in 6h (sensible default)
        scheduled_arrival = datetime.now(tz=timezone.utc) + timedelta(hours=6)

    result = jit_engine.calculate(
        vessel_lat=float(pos.lat),
        vessel_lon=float(pos.lon),
        current_speed=float(pos.sog_knots) if pos.sog_knots is not None else 0.0,
        scheduled_arrival=scheduled_arrival,
    )

    rec = _persist_recommendation(
        session,
        vessel_id=payload.vessel_id,
        booking_id=payload.booking_id,
        result=result,
        scheduled_arrival=scheduled_arrival,
    )
    await session.commit()
    await session.refresh(rec)
    return _rec_to_out(rec)


@router.get("/recommendations/{vessel_id}", response_model=List[JITRecommendationOut])
async def list_recommendations(
    vessel_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> List[JITRecommendationOut]:
    stmt = (
        select(JitRecommendation)
        .where(JitRecommendation.vessel_id == vessel_id)
        .order_by(desc(JitRecommendation.issued_at))
        .limit(20)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_rec_to_out(r) for r in rows]


@router.get("/fleet-status", response_model=List[FleetVesselStatus])
async def fleet_status(
    session: AsyncSession = Depends(get_session),
) -> List[FleetVesselStatus]:
    return await compute_fleet_status(session)


# ---------------------------------------------------------------------------
# Reusable fleet-status computation (also used by WebSocket broadcaster)
# ---------------------------------------------------------------------------

async def compute_fleet_status(session: AsyncSession) -> List[FleetVesselStatus]:
    # All active vessels with a SCHEDULED booking ahead of now.
    stmt = (
        select(Vessel, PortBooking)
        .join(PortBooking, PortBooking.vessel_id == Vessel.id)
        .where(
            Vessel.status == "active",
            PortBooking.status.in_(("scheduled", "confirmed")),
            PortBooking.eta >= datetime.now(tz=timezone.utc) - timedelta(hours=12),
        )
        .order_by(PortBooking.eta.asc())
    )
    pairs = (await session.execute(stmt)).all()

    out: List[FleetVesselStatus] = []
    for vessel, booking in pairs:
        # Latest position
        pos = (
            await session.execute(
                select(VesselPosition)
                .where(VesselPosition.vessel_id == vessel.id)
                .order_by(desc(VesselPosition.recorded_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if not pos:
            continue

        result = jit_engine.calculate(
            vessel_lat=float(pos.lat),
            vessel_lon=float(pos.lon),
            current_speed=float(pos.sog_knots) if pos.sog_knots is not None else 0.0,
            scheduled_arrival=booking.eta,
            port_lat=settings.BAKU_PORT_LAT,
            port_lon=settings.BAKU_PORT_LON,
        )
        out.append(
            FleetVesselStatus(
                vessel_id=vessel.id,
                vessel_name=vessel.name,
                booking_id=booking.id,
                lat=float(pos.lat),
                lon=float(pos.lon),
                current_speed=result["current_speed"],
                recommended_speed=result["recommended_speed"],
                distance_nm=result["distance_nm"],
                time_available_hours=result["time_available_hours"],
                status=result["status"],
                fuel_saved_liters=result["fuel_saved_liters"],
                co2_saved_kg=result["co2_saved_kg"],
                scheduled_arrival=booking.eta,
            )
        )
    return out
