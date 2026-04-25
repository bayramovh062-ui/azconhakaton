"""Ship Owner panel — endpoints scoped to the operator's vessels."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.utils import get_current_user
from backend.database import get_session
from backend.models import (
    JitRecommendation,
    PortBooking,
    User,
    Vessel,
    VesselPosition,
)

router = APIRouter(prefix="/owner", tags=["owner"])


# Marine fuel cost in USD per liter (mock baseline for cost-saving USD figures)
USD_PER_LITER = 0.85
LITERS_PER_TONNE = 1.0 / 0.00085  # ≈ 1176


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _aware(dt):
    if dt is None:
        return None
    return dt if getattr(dt, "tzinfo", None) else dt.replace(tzinfo=timezone.utc)


def _resolve_company(user: User, override: Optional[str]) -> str:
    """Admins may pass `?company=...`; owners are scoped to their own."""
    if user.role == "admin":
        return override or user.operator_company or ""
    return user.operator_company or ""


# --------------------------------------------------------------------------- #
# Schemas                                                                     #
# --------------------------------------------------------------------------- #

class OwnerSummary(BaseModel):
    company: str
    vessel_count: int
    active_vessels: int
    upcoming_bookings: int
    in_port_now: int
    total_fuel_saved_liters: float
    total_co2_saved_kg: float
    cost_savings_usd: float
    overspeed_alerts: int
    optimal_arrivals: int


class OwnerVesselRow(BaseModel):
    id: uuid.UUID
    name: str
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    flag: Optional[str] = None
    vessel_type: str
    status: str
    last_lat: Optional[float] = None
    last_lon: Optional[float] = None
    last_sog: Optional[float] = None
    last_seen: Optional[datetime] = None
    co2_saved_kg: float = 0.0
    next_eta: Optional[datetime] = None
    next_berth: Optional[str] = None


class TrendPoint(BaseModel):
    day: str
    co2_saved_kg: float
    fuel_saved_liters: float


# --------------------------------------------------------------------------- #
# Endpoints                                                                   #
# --------------------------------------------------------------------------- #

@router.get("/summary", response_model=OwnerSummary)
async def summary(
    company: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> OwnerSummary:
    target = _resolve_company(user, company)
    if not target:
        raise HTTPException(status_code=400, detail="No operator_company on user")

    # Vessels of this operator
    vessels = (
        await session.execute(select(Vessel).where(Vessel.operator == target))
    ).scalars().all()
    vessel_ids = [v.id for v in vessels]
    if not vessel_ids:
        return OwnerSummary(
            company=target, vessel_count=0, active_vessels=0, upcoming_bookings=0,
            in_port_now=0, total_fuel_saved_liters=0, total_co2_saved_kg=0,
            cost_savings_usd=0, overspeed_alerts=0, optimal_arrivals=0,
        )

    active = sum(1 for v in vessels if v.status == "active")

    # Bookings
    now = datetime.now(tz=timezone.utc)
    upcoming = (
        await session.execute(
            select(func.count())
            .select_from(PortBooking)
            .where(PortBooking.vessel_id.in_(vessel_ids))
            .where(PortBooking.eta >= now)
            .where(PortBooking.status.in_(["scheduled", "confirmed"]))
        )
    ).scalar_one()
    in_port = (
        await session.execute(
            select(func.count())
            .select_from(PortBooking)
            .where(PortBooking.vessel_id.in_(vessel_ids))
            .where(PortBooking.status == "in_progress")
        )
    ).scalar_one()

    # JIT aggregates
    fuel_t = (
        await session.execute(
            select(func.coalesce(func.sum(JitRecommendation.fuel_savings_t), 0))
            .where(JitRecommendation.vessel_id.in_(vessel_ids))
        )
    ).scalar_one() or 0
    co2 = (
        await session.execute(
            select(func.coalesce(func.sum(JitRecommendation.co2_savings_kg), 0))
            .where(JitRecommendation.vessel_id.in_(vessel_ids))
        )
    ).scalar_one() or 0
    overspeed = (
        await session.execute(
            select(func.count())
            .select_from(JitRecommendation)
            .where(JitRecommendation.vessel_id.in_(vessel_ids))
            .where(JitRecommendation.status == "OVERSPEED")
        )
    ).scalar_one() or 0
    optimal = (
        await session.execute(
            select(func.count())
            .select_from(JitRecommendation)
            .where(JitRecommendation.vessel_id.in_(vessel_ids))
            .where(JitRecommendation.status == "OPTIMAL")
        )
    ).scalar_one() or 0

    fuel_l = float(fuel_t) * LITERS_PER_TONNE

    return OwnerSummary(
        company=target,
        vessel_count=len(vessels),
        active_vessels=active,
        upcoming_bookings=int(upcoming),
        in_port_now=int(in_port),
        total_fuel_saved_liters=round(fuel_l, 2),
        total_co2_saved_kg=round(float(co2), 2),
        cost_savings_usd=round(fuel_l * USD_PER_LITER, 2),
        overspeed_alerts=int(overspeed),
        optimal_arrivals=int(optimal),
    )


@router.get("/vessels", response_model=List[OwnerVesselRow])
async def vessels(
    company: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[OwnerVesselRow]:
    target = _resolve_company(user, company)
    rows = (
        await session.execute(select(Vessel).where(Vessel.operator == target).order_by(Vessel.name))
    ).scalars().all()

    out: List[OwnerVesselRow] = []
    for v in rows:
        # Latest position
        pos = (
            await session.execute(
                select(VesselPosition)
                .where(VesselPosition.vessel_id == v.id)
                .order_by(desc(VesselPosition.recorded_at))
                .limit(1)
            )
        ).scalar_one_or_none()

        co2 = (
            await session.execute(
                select(func.coalesce(func.sum(JitRecommendation.co2_savings_kg), 0))
                .where(JitRecommendation.vessel_id == v.id)
            )
        ).scalar_one() or 0

        # Next booking
        next_bk = (
            await session.execute(
                select(PortBooking)
                .where(PortBooking.vessel_id == v.id)
                .where(PortBooking.status.in_(["scheduled", "confirmed", "in_progress"]))
                .order_by(PortBooking.eta.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        next_berth_code = None
        if next_bk and next_bk.berth_id:
            from backend.models import Berth
            berth = await session.get(Berth, next_bk.berth_id)
            next_berth_code = berth.code if berth else None

        out.append(OwnerVesselRow(
            id=v.id, name=v.name, imo=v.imo, mmsi=v.mmsi,
            flag=v.flag, vessel_type=v.vessel_type, status=v.status,
            last_lat=float(pos.lat) if pos else None,
            last_lon=float(pos.lon) if pos else None,
            last_sog=float(pos.sog_knots) if pos and pos.sog_knots is not None else None,
            last_seen=_aware(pos.recorded_at) if pos else None,
            co2_saved_kg=round(float(co2), 2),
            next_eta=_aware(next_bk.eta) if next_bk else None,
            next_berth=next_berth_code,
        ))
    return out


@router.get("/trend", response_model=List[TrendPoint])
async def trend(
    days: int = Query(default=30, ge=1, le=180),
    company: Optional[str] = Query(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> List[TrendPoint]:
    target = _resolve_company(user, company)
    vessels = (
        await session.execute(
            select(Vessel.id).where(Vessel.operator == target)
        )
    ).scalars().all()
    if not vessels:
        return []

    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    day_col = func.date(JitRecommendation.issued_at).label("day")
    rows = (
        await session.execute(
            select(
                day_col,
                func.coalesce(func.sum(JitRecommendation.fuel_savings_t), 0),
                func.coalesce(func.sum(JitRecommendation.co2_savings_kg), 0),
            )
            .where(JitRecommendation.vessel_id.in_(vessels))
            .where(JitRecommendation.issued_at >= since)
            .group_by(day_col)
            .order_by(day_col.asc())
        )
    ).all()

    return [
        TrendPoint(
            day=str(d),
            fuel_saved_liters=round(float(ft) * LITERS_PER_TONNE, 2),
            co2_saved_kg=round(float(co2), 2),
        )
        for d, ft, co2 in rows
    ]
