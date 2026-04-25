"""Derived alerts feed.

Synthesises an alert stream from existing data:
  * OVERSPEED / UNDERSPEED JIT recommendations  -> JIT alerts
  * Bookings with status='delayed'              -> SLA alerts
  * Berths with status='maintenance' / 'closed' -> infra alerts
  * Vessels last-seen > 6h ago                  -> telemetry-gap alerts

This avoids a separate alerts table while giving the UI something to render.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.models import (
    Berth,
    JitRecommendation,
    PortBooking,
    Vessel,
    VesselPosition,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    """SQLite returns naive datetimes; coerce to UTC-aware."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class Alert(BaseModel):
    id: str
    severity: str        # critical | warning | info
    category: str        # jit | sla | infra | telemetry
    title: str
    message: str
    vessel_id: Optional[uuid.UUID] = None
    vessel_name: Optional[str] = None
    occurred_at: datetime
    acknowledged: bool = False


async def _build_alerts(
    session: AsyncSession,
    severity: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
) -> List[Alert]:
    out: List[Alert] = []
    now = datetime.now(tz=timezone.utc)

    # 1) JIT recommendations (last 48h)
    cutoff = now - timedelta(hours=48)
    stmt = (
        select(JitRecommendation, Vessel.name)
        .join(Vessel, Vessel.id == JitRecommendation.vessel_id)
        .where(JitRecommendation.issued_at >= cutoff)
        .where(JitRecommendation.status.in_(["OVERSPEED", "UNDERSPEED", "BERTH_READY"]))
        .order_by(desc(JitRecommendation.issued_at))
        .limit(80)
    )
    for rec, vname in (await session.execute(stmt)).all():
        sev = "critical" if rec.status == "OVERSPEED" else "warning"
        if rec.status == "BERTH_READY":
            sev = "info"
        out.append(Alert(
            id=f"jit:{rec.id}",
            severity=sev,
            category="jit",
            title=f"{rec.status.title()} — {vname}",
            message=f"Recommended {float(rec.recommended_speed):.1f} kn — "
                    f"potential CO₂ saving {float(rec.co2_savings_kg or 0):.0f} kg",
            vessel_id=rec.vessel_id,
            vessel_name=vname,
            occurred_at=_aware(rec.issued_at),
        ))

    # 2) Delayed bookings
    stmt2 = (
        select(PortBooking, Vessel.name)
        .join(Vessel, Vessel.id == PortBooking.vessel_id)
        .where(PortBooking.status.in_(["delayed", "cancelled"]))
        .order_by(desc(PortBooking.eta))
        .limit(15)
    )
    for bk, vname in (await session.execute(stmt2)).all():
        out.append(Alert(
            id=f"booking:{bk.id}",
            severity="warning" if bk.status == "delayed" else "info",
            category="sla",
            title=f"Booking {bk.booking_reference} — {bk.status}",
            message=f"{vname} scheduled at {bk.eta:%Y-%m-%d %H:%M UTC}",
            vessel_id=bk.vessel_id,
            vessel_name=vname,
            occurred_at=_aware(bk.updated_at or bk.created_at),
        ))

    # 3) Maintenance/closed berths
    stmt3 = select(Berth).where(Berth.status.in_(["maintenance", "closed"]))
    for berth in (await session.execute(stmt3)).scalars().all():
        out.append(Alert(
            id=f"berth:{berth.id}",
            severity="warning" if berth.status == "maintenance" else "critical",
            category="infra",
            title=f"Berth {berth.code} — {berth.status}",
            message=berth.name,
            occurred_at=_aware(berth.updated_at) or now,
        ))

    # 4) Telemetry gaps (vessels with no position in last 6h)
    last_seen_subq = (
        select(
            VesselPosition.vessel_id,
            func.max(VesselPosition.recorded_at).label("last_seen"),
        )
        .group_by(VesselPosition.vessel_id)
        .subquery()
    )
    stmt4 = (
        select(Vessel, last_seen_subq.c.last_seen)
        .outerjoin(last_seen_subq, last_seen_subq.c.vessel_id == Vessel.id)
        .where(Vessel.status == "active")
    )
    six_h_ago = now - timedelta(hours=6)
    for vessel, last_seen in (await session.execute(stmt4)).all():
        last_seen_aw = _aware(last_seen)
        if last_seen_aw is None or last_seen_aw < six_h_ago:
            ago = "no AIS yet" if last_seen_aw is None else f"last seen {last_seen_aw:%Y-%m-%d %H:%M UTC}"
            out.append(Alert(
                id=f"gap:{vessel.id}",
                severity="warning",
                category="telemetry",
                title=f"Telemetry gap — {vessel.name}",
                message=f"{ago}",
                vessel_id=vessel.id,
                vessel_name=vessel.name,
                occurred_at=last_seen_aw or now - timedelta(days=1),
            ))

    if severity:
        out = [a for a in out if a.severity == severity]
    if category:
        out = [a for a in out if a.category == category]

    out.sort(key=lambda a: a.occurred_at, reverse=True)
    return out[:limit]


@router.get("", response_model=List[Alert])
async def list_alerts(
    severity: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> List[Alert]:
    return await _build_alerts(session, severity, category, limit)


class AlertCounts(BaseModel):
    critical: int
    warning: int
    info: int
    total: int


@router.get("/counts", response_model=AlertCounts)
async def counts(session: AsyncSession = Depends(get_session)) -> AlertCounts:
    rows = await _build_alerts(session, limit=200)
    by_sev = {"critical": 0, "warning": 0, "info": 0}
    for a in rows:
        by_sev[a.severity] = by_sev.get(a.severity, 0) + 1
    return AlertCounts(**by_sev, total=len(rows))
