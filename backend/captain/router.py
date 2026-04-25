"""Ship Captain cockpit — endpoints scoped to the captain's vessel."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth.utils import get_current_user
from backend.database import get_session
from backend.jit.engine import jit_engine
from backend.models import (
    Berth,
    JitRecommendation,
    PortBooking,
    User,
    Vessel,
    VesselPosition,
    VoyageLog,
)
from backend.config import settings

router = APIRouter(prefix="/captain", tags=["captain"])


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _aware(dt):
    if dt is None:
        return None
    return dt if getattr(dt, "tzinfo", None) else dt.replace(tzinfo=timezone.utc)


def _resolve_vessel_id(user: User, override: Optional[uuid.UUID]) -> uuid.UUID:
    """Admins may target any vessel via `?vessel_id=`; captains are pinned."""
    if user.role == "admin":
        if not override:
            raise HTTPException(status_code=400, detail="admin must pass ?vessel_id=")
        return override
    if not user.vessel_id:
        raise HTTPException(status_code=403, detail="No vessel assigned to user")
    return user.vessel_id


# --------------------------------------------------------------------------- #
# Schemas                                                                     #
# --------------------------------------------------------------------------- #

class VoyageView(BaseModel):
    vessel_id: uuid.UUID
    vessel_name: str
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    flag: Optional[str] = None

    last_lat: Optional[float] = None
    last_lon: Optional[float] = None
    last_sog: Optional[float] = None
    last_cog: Optional[float] = None
    last_seen: Optional[datetime] = None
    nav_status: Optional[str] = None

    booking_id: Optional[uuid.UUID] = None
    booking_ref: Optional[str] = None
    berth_code: Optional[str] = None
    berth_name: Optional[str] = None
    eta: Optional[datetime] = None

    distance_to_port_nm: Optional[float] = None
    time_available_hours: Optional[float] = None
    recommended_speed: Optional[float] = None
    jit_status: Optional[str] = None
    fuel_saved_liters: Optional[float] = None
    co2_saved_kg: Optional[float] = None
    latest_recommendation_id: Optional[uuid.UUID] = None


class VoyageLogIn(BaseModel):
    note: str
    kind: str = "entry"
    booking_id: Optional[uuid.UUID] = None


class VoyageLogOut(BaseModel):
    id: uuid.UUID
    vessel_id: uuid.UUID
    author_id: Optional[uuid.UUID] = None
    author_name: Optional[str] = None
    booking_id: Optional[uuid.UUID] = None
    kind: str
    note: str
    created_at: datetime


class CaptainPositionIn(BaseModel):
    lat: float
    lon: float
    speed_over_ground: Optional[float] = None
    course_over_ground: Optional[float] = None
    heading: Optional[float] = None
    nav_status: Optional[str] = "under_way_using_engine"


class JitAckIn(BaseModel):
    decision: str  # 'accepted' | 'rejected' | 'applied'
    note: Optional[str] = None


# --------------------------------------------------------------------------- #
# /captain/voyage — single source of truth for the cockpit                    #
# --------------------------------------------------------------------------- #

@router.get("/voyage", response_model=VoyageView)
async def voyage(
    vessel_id: Optional[uuid.UUID] = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> VoyageView:
    vid = _resolve_vessel_id(user, vessel_id)
    vessel = await session.get(Vessel, vid)
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")

    pos = (
        await session.execute(
            select(VesselPosition)
            .where(VesselPosition.vessel_id == vid)
            .order_by(desc(VesselPosition.recorded_at))
            .limit(1)
        )
    ).scalar_one_or_none()

    booking = (
        await session.execute(
            select(PortBooking)
            .where(PortBooking.vessel_id == vid)
            .where(PortBooking.status.in_(["scheduled", "confirmed", "in_progress"]))
            .order_by(PortBooking.eta.asc())
            .limit(1)
        )
    ).scalar_one_or_none()

    berth = await session.get(Berth, booking.berth_id) if booking and booking.berth_id else None

    # Latest JIT recommendation
    latest_rec = (
        await session.execute(
            select(JitRecommendation)
            .where(JitRecommendation.vessel_id == vid)
            .order_by(desc(JitRecommendation.issued_at))
            .limit(1)
        )
    ).scalar_one_or_none()

    # Live JIT computed on the fly if we have position & booking
    jit = None
    if pos and booking:
        jit = jit_engine.calculate(
            vessel_lat=float(pos.lat),
            vessel_lon=float(pos.lon),
            current_speed=float(pos.sog_knots) if pos.sog_knots is not None else 0.0,
            scheduled_arrival=_aware(booking.eta),
            port_lat=settings.BAKU_PORT_LAT,
            port_lon=settings.BAKU_PORT_LON,
        )

    return VoyageView(
        vessel_id=vid,
        vessel_name=vessel.name,
        imo=vessel.imo, mmsi=vessel.mmsi, flag=vessel.flag,
        last_lat=float(pos.lat) if pos else None,
        last_lon=float(pos.lon) if pos else None,
        last_sog=float(pos.sog_knots) if pos and pos.sog_knots is not None else None,
        last_cog=float(pos.cog_deg) if pos and pos.cog_deg is not None else None,
        last_seen=_aware(pos.recorded_at) if pos else None,
        nav_status=pos.nav_status if pos else None,
        booking_id=booking.id if booking else None,
        booking_ref=booking.booking_reference if booking else None,
        berth_code=berth.code if berth else None,
        berth_name=berth.name if berth else None,
        eta=_aware(booking.eta) if booking else None,
        distance_to_port_nm=jit["distance_nm"] if jit else None,
        time_available_hours=jit["time_available_hours"] if jit else None,
        recommended_speed=jit["recommended_speed"] if jit else None,
        jit_status=jit["status"] if jit else None,
        fuel_saved_liters=jit["fuel_saved_liters"] if jit else None,
        co2_saved_kg=jit["co2_saved_kg"] if jit else None,
        latest_recommendation_id=latest_rec.id if latest_rec else None,
    )


# --------------------------------------------------------------------------- #
# /captain/log                                                                #
# --------------------------------------------------------------------------- #

@router.get("/log", response_model=List[VoyageLogOut])
async def list_log(
    vessel_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[VoyageLogOut]:
    vid = _resolve_vessel_id(user, vessel_id)
    rows = (
        await session.execute(
            select(VoyageLog, User.full_name)
            .outerjoin(User, User.id == VoyageLog.author_id)
            .where(VoyageLog.vessel_id == vid)
            .order_by(desc(VoyageLog.created_at))
            .limit(limit)
        )
    ).all()
    return [
        VoyageLogOut(
            id=lg.id, vessel_id=lg.vessel_id, author_id=lg.author_id,
            author_name=author_name, booking_id=lg.booking_id,
            kind=lg.kind, note=lg.note,
            created_at=_aware(lg.created_at),
        )
        for lg, author_name in rows
    ]


@router.post("/log", response_model=VoyageLogOut)
async def add_log(
    payload: VoyageLogIn,
    vessel_id: Optional[uuid.UUID] = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> VoyageLogOut:
    vid = _resolve_vessel_id(user, vessel_id)
    if payload.kind not in {"entry", "observation", "incident", "fuel", "eta_update"}:
        raise HTTPException(status_code=400, detail="Invalid kind")
    log = VoyageLog(
        vessel_id=vid,
        author_id=user.id,
        booking_id=payload.booking_id,
        kind=payload.kind,
        note=payload.note,
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return VoyageLogOut(
        id=log.id, vessel_id=log.vessel_id, author_id=log.author_id,
        author_name=user.full_name, booking_id=log.booking_id,
        kind=log.kind, note=log.note, created_at=_aware(log.created_at),
    )


# --------------------------------------------------------------------------- #
# Captain — submit a position (manual telemetry)                              #
# --------------------------------------------------------------------------- #

@router.post("/position")
async def submit_position(
    payload: CaptainPositionIn,
    vessel_id: Optional[uuid.UUID] = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    vid = _resolve_vessel_id(user, vessel_id)
    if not (-90 <= payload.lat <= 90) or not (-180 <= payload.lon <= 180):
        raise HTTPException(status_code=400, detail="lat/lon out of range")
    pos = VesselPosition(
        vessel_id=vid,
        lat=payload.lat, lon=payload.lon,
        sog_knots=Decimal(str(payload.speed_over_ground)) if payload.speed_over_ground is not None else None,
        cog_deg=Decimal(str(payload.course_over_ground)) if payload.course_over_ground is not None else None,
        heading_deg=Decimal(str(payload.heading)) if payload.heading is not None else None,
        nav_status=payload.nav_status,
        source="captain",
        recorded_at=datetime.now(tz=timezone.utc),
    )
    session.add(pos)
    await session.commit()
    return {"ok": True, "id": pos.id}


# --------------------------------------------------------------------------- #
# Captain — acknowledge a JIT recommendation                                  #
# --------------------------------------------------------------------------- #

@router.post("/jit/{rec_id}/acknowledge")
async def acknowledge_jit(
    rec_id: uuid.UUID,
    payload: JitAckIn,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rec = await session.get(JitRecommendation, rec_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    if user.role != "admin" and user.vessel_id != rec.vessel_id:
        raise HTTPException(status_code=403, detail="Not your vessel")
    if payload.decision not in {"accepted", "rejected", "applied"}:
        raise HTTPException(status_code=400, detail="Invalid decision")

    rec.status = payload.decision
    if payload.note:
        session.add(VoyageLog(
            vessel_id=rec.vessel_id, author_id=user.id, booking_id=rec.booking_id,
            kind="entry", note=f"[JIT {payload.decision}] {payload.note}",
        ))
    await session.commit()
    return {"ok": True, "status": rec.status}
