"""ESG dashboard endpoints."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_session
from backend.jit.router import LITERS_TO_TONNES  # noqa: F401  -- doc reference
from backend.models import JitRecommendation

router = APIRouter(prefix="/esg", tags=["esg"])

# Fleet-wide constants (mirrors backend/jit/router.py)
_TONNES_TO_LITERS = 1.0 / 0.00085  # ≈ 1176.47


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ESGSummary(BaseModel):
    total_fuel_saved_liters: float
    total_co2_saved_kg: float
    total_optimal_arrivals: int
    total_overspeed_events: int
    total_underspeed_events: int
    vessels_tracked: int
    co2_reduction_percent: float


class ESGDailyPoint(BaseModel):
    day: date
    fuel_saved_liters: float
    co2_saved_kg: float
    optimal_arrivals: int
    overspeed_events: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/summary", response_model=ESGSummary)
async def summary(session: AsyncSession = Depends(get_session)) -> ESGSummary:
    fuel_t_col = func.coalesce(func.sum(JitRecommendation.fuel_savings_t), 0)
    co2_col = func.coalesce(func.sum(JitRecommendation.co2_savings_kg), 0)
    optimal_col = func.coalesce(
        func.sum(case((JitRecommendation.status == "OPTIMAL", 1), else_=0)), 0
    )
    overspeed_col = func.coalesce(
        func.sum(case((JitRecommendation.status == "OVERSPEED", 1), else_=0)), 0
    )
    underspeed_col = func.coalesce(
        func.sum(case((JitRecommendation.status == "UNDERSPEED", 1), else_=0)), 0
    )
    vessels_col = func.count(distinct(JitRecommendation.vessel_id))

    row = (
        await session.execute(
            select(
                fuel_t_col,
                co2_col,
                optimal_col,
                overspeed_col,
                underspeed_col,
                vessels_col,
            )
        )
    ).one()

    fuel_t, co2, optimal, overspeed, underspeed, vessels = row
    fuel_liters = float(fuel_t) * _TONNES_TO_LITERS
    co2_saved = float(co2)

    # Baseline = what would have been emitted = saved + a notional non-saved
    # baseline equal to (saved / FUEL_CONSUMPTION_RATE) approximation.
    # Pragmatic: assume saved represents 15% of an optimized voyage's footprint;
    # therefore total baseline ≈ saved / 0.15.
    if co2_saved > 0:
        baseline = co2_saved / 0.15
        reduction_pct = (co2_saved / baseline) * 100.0
    else:
        reduction_pct = 0.0

    return ESGSummary(
        total_fuel_saved_liters=round(fuel_liters, 3),
        total_co2_saved_kg=round(co2_saved, 3),
        total_optimal_arrivals=int(optimal),
        total_overspeed_events=int(overspeed),
        total_underspeed_events=int(underspeed),
        vessels_tracked=int(vessels),
        co2_reduction_percent=round(reduction_pct, 2),
    )


@router.get("/daily", response_model=List[ESGDailyPoint])
async def daily(
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_session),
) -> List[ESGDailyPoint]:
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    day_col = func.date_trunc("day", JitRecommendation.issued_at).label("day")
    stmt = (
        select(
            day_col,
            func.coalesce(func.sum(JitRecommendation.fuel_savings_t), 0),
            func.coalesce(func.sum(JitRecommendation.co2_savings_kg), 0),
            func.coalesce(
                func.sum(case((JitRecommendation.status == "OPTIMAL", 1), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((JitRecommendation.status == "OVERSPEED", 1), else_=0)), 0
            ),
        )
        .where(JitRecommendation.issued_at >= since)
        .group_by(day_col)
        .order_by(day_col.asc())
    )
    rows = (await session.execute(stmt)).all()

    out: List[ESGDailyPoint] = []
    for day_dt, fuel_t, co2, optimal, overspeed in rows:
        out.append(
            ESGDailyPoint(
                day=day_dt.date() if isinstance(day_dt, datetime) else day_dt,
                fuel_saved_liters=round(float(fuel_t) * _TONNES_TO_LITERS, 3),
                co2_saved_kg=round(float(co2), 3),
                optimal_arrivals=int(optimal),
                overspeed_events=int(overspeed),
            )
        )
    return out
