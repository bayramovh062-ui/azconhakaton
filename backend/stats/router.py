"""Aggregate statistics: berth utilization, top vessels, fleet mix, activity."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_session
from backend.models import Berth, JitRecommendation, PortBooking, Vessel

router = APIRouter(prefix="/stats", tags=["stats"])


# --------------------------------------------------------------------------- #
# Berth utilization                                                            #
# --------------------------------------------------------------------------- #

class BerthRow(BaseModel):
    id: str
    code: str
    name: str
    status: str
    bookings: int
    occupied_hours: float
    utilization_pct: float


@router.get("/berth-utilization", response_model=List[BerthRow])
async def berth_utilization(
    days: int = Query(default=14, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
) -> List[BerthRow]:
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    window_h = days * 24

    rows = (
        await session.execute(
            select(Berth, func.count(PortBooking.id), PortBooking.actual_arrival, PortBooking.actual_departure, PortBooking.eta, PortBooking.etd)
            .outerjoin(PortBooking, PortBooking.berth_id == Berth.id)
        )
    ).all()

    # Aggregate per berth manually for clarity
    per_berth: dict[str, dict] = {}
    for berth, _cnt, *_rest in rows:
        per_berth.setdefault(str(berth.id), {"berth": berth, "bookings": 0, "hours": 0.0})

    bk_rows = (
        await session.execute(
            select(PortBooking).where(PortBooking.eta >= since)
        )
    ).scalars().all()

    for bk in bk_rows:
        bucket = per_berth.setdefault(str(bk.berth_id), {"berth": None, "bookings": 0, "hours": 0.0})
        bucket["bookings"] += 1
        start = bk.actual_arrival or bk.eta
        end = bk.actual_departure or bk.etd
        if start and end and end > start:
            bucket["hours"] += (end - start).total_seconds() / 3600.0

    out: List[BerthRow] = []
    for v in per_berth.values():
        b = v["berth"]
        if not b:
            continue
        util = (v["hours"] / window_h) * 100 if window_h else 0
        out.append(BerthRow(
            id=str(b.id), code=b.code, name=b.name, status=b.status,
            bookings=v["bookings"], occupied_hours=round(v["hours"], 2),
            utilization_pct=round(util, 2),
        ))
    out.sort(key=lambda r: r.code)
    return out


# --------------------------------------------------------------------------- #
# Top vessels (by total CO2 saved)                                             #
# --------------------------------------------------------------------------- #

class TopVessel(BaseModel):
    vessel_id: str
    vessel_name: str
    operator: str | None = None
    flag: str | None = None
    co2_saved_kg: float
    optimal_count: int
    overspeed_count: int
    total_recs: int


@router.get("/top-vessels", response_model=List[TopVessel])
async def top_vessels(
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
) -> List[TopVessel]:
    optimal_col = func.coalesce(
        func.sum(case((JitRecommendation.status == "OPTIMAL", 1), else_=0)), 0
    )
    overspeed_col = func.coalesce(
        func.sum(case((JitRecommendation.status == "OVERSPEED", 1), else_=0)), 0
    )
    co2_col = func.coalesce(func.sum(JitRecommendation.co2_savings_kg), 0)
    cnt_col = func.count(JitRecommendation.id)

    stmt = (
        select(Vessel, co2_col, optimal_col, overspeed_col, cnt_col)
        .outerjoin(JitRecommendation, JitRecommendation.vessel_id == Vessel.id)
        .group_by(Vessel.id)
        .order_by(co2_col.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        TopVessel(
            vessel_id=str(v.id), vessel_name=v.name,
            operator=v.operator, flag=v.flag,
            co2_saved_kg=round(float(co2 or 0), 2),
            optimal_count=int(opt), overspeed_count=int(over),
            total_recs=int(cnt),
        )
        for v, co2, opt, over, cnt in rows
    ]


# --------------------------------------------------------------------------- #
# Fleet mix by type / flag                                                     #
# --------------------------------------------------------------------------- #

class MixRow(BaseModel):
    label: str
    value: int


@router.get("/fleet-mix", response_model=dict)
async def fleet_mix(session: AsyncSession = Depends(get_session)) -> dict:
    by_type = (
        await session.execute(
            select(Vessel.vessel_type, func.count())
            .group_by(Vessel.vessel_type)
            .order_by(func.count().desc())
        )
    ).all()
    by_flag = (
        await session.execute(
            select(Vessel.flag, func.count())
            .where(Vessel.flag.isnot(None))
            .group_by(Vessel.flag)
            .order_by(func.count().desc())
        )
    ).all()
    return {
        "by_type": [{"label": t or "unknown", "value": int(c)} for t, c in by_type],
        "by_flag": [{"label": f or "unknown", "value": int(c)} for f, c in by_flag],
    }


# --------------------------------------------------------------------------- #
# Mock weather feed for Baku Port                                              #
# --------------------------------------------------------------------------- #

class Weather(BaseModel):
    temp_c: float
    wind_speed_knots: float
    wind_dir_deg: float
    wave_height_m: float
    visibility_nm: float
    condition: str
    advisory: str | None = None


@router.get("/weather", response_model=Weather)
async def weather() -> Weather:
    # Deterministic-ish: vary per hour so it changes during a session
    rnd = random.Random(int(datetime.now().timestamp() // 600))
    cond_pool = ["clear", "partly cloudy", "cloudy", "light rain", "haze", "windy"]
    cond = rnd.choice(cond_pool)
    wind = round(rnd.uniform(2, 22), 1)
    return Weather(
        temp_c=round(rnd.uniform(8, 24), 1),
        wind_speed_knots=wind,
        wind_dir_deg=round(rnd.uniform(0, 360), 0),
        wave_height_m=round(rnd.uniform(0.2, 1.8), 2),
        visibility_nm=round(rnd.uniform(4, 10), 1),
        condition=cond,
        advisory="High wind — pilotage may be delayed" if wind > 18 else None,
    )


# --------------------------------------------------------------------------- #
# Recent activity feed (lightweight derivation)                                #
# --------------------------------------------------------------------------- #

class ActivityItem(BaseModel):
    timestamp: datetime
    kind: str    # booking | jit | telemetry
    text: str


@router.get("/activity", response_model=List[ActivityItem])
async def activity(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> List[ActivityItem]:
    items: list[ActivityItem] = []

    # Recent bookings
    bk_rows = (
        await session.execute(
            select(PortBooking, Vessel.name)
            .join(Vessel, Vessel.id == PortBooking.vessel_id)
            .order_by(PortBooking.created_at.desc())
            .limit(20)
        )
    ).all()
    for bk, vname in bk_rows:
        items.append(ActivityItem(
            timestamp=bk.created_at,
            kind="booking",
            text=f"Booking {bk.booking_reference} • {vname} → {bk.status}",
        ))

    # Recent JIT recs
    jit_rows = (
        await session.execute(
            select(JitRecommendation, Vessel.name)
            .join(Vessel, Vessel.id == JitRecommendation.vessel_id)
            .order_by(JitRecommendation.issued_at.desc())
            .limit(20)
        )
    ).all()
    for rec, vname in jit_rows:
        items.append(ActivityItem(
            timestamp=rec.issued_at,
            kind="jit",
            text=f"JIT {rec.status} • {vname} @ {float(rec.recommended_speed):.1f} kn",
        ))

    items.sort(key=lambda x: x.timestamp, reverse=True)
    return items[:limit]
