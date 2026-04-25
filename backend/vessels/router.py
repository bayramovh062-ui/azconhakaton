"""Vessels and AIS positions REST router."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import hashlib
import random as _random
from datetime import timedelta as _timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.utils import get_current_user, require_roles
from backend.database import get_session
from backend.models import User, Vessel, VesselPosition

from .schemas import (
    VesselCreate,
    VesselOut,
    VesselPositionCreate,
    VesselPositionOut,
)

router = APIRouter(prefix="/vessels", tags=["vessels"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vessel_to_out(v: Vessel) -> VesselOut:
    return VesselOut(
        id=v.id,
        imo=v.imo,
        mmsi=v.mmsi,
        name=v.name,
        flag=v.flag,
        vessel_type=v.vessel_type,
        length_meters=float(v.length_m) if v.length_m is not None else None,
        # max_speed isn't a column — surface a sane default for clients
        max_speed_knots=14.0,
        operator=v.operator,
        status=v.status,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


def _position_to_out(p: VesselPosition) -> VesselPositionOut:
    return VesselPositionOut(
        id=p.id,
        vessel_id=p.vessel_id,
        lat=float(p.lat),
        lon=float(p.lon),
        speed_over_ground=float(p.sog_knots) if p.sog_knots is not None else None,
        course_over_ground=float(p.cog_deg) if p.cog_deg is not None else None,
        heading=float(p.heading_deg) if p.heading_deg is not None else None,
        nav_status=p.nav_status,
        source=p.source,
        recorded_at=p.recorded_at,
        created_at=p.created_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[VesselOut])
async def list_vessels(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> List[VesselOut]:
    stmt = select(Vessel)
    if status_filter:
        stmt = stmt.where(Vessel.status == status_filter)
    stmt = stmt.order_by(Vessel.name)
    rows = (await session.execute(stmt)).scalars().all()
    return [_vessel_to_out(v) for v in rows]


@router.get("/{vessel_id}", response_model=VesselOut)
async def get_vessel(
    vessel_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> VesselOut:
    vessel = await session.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return _vessel_to_out(vessel)


@router.post(
    "",
    response_model=VesselOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin"))],
)
async def create_vessel(
    payload: VesselCreate,
    session: AsyncSession = Depends(get_session),
) -> VesselOut:
    vessel = Vessel(
        imo=payload.imo or f"PENDING-{uuid.uuid4().hex[:8].upper()}",
        mmsi=payload.mmsi,
        name=payload.name,
        flag=payload.flag,
        vessel_type=payload.vessel_type,
        length_m=payload.length_meters,
        operator=payload.operator,
    )
    session.add(vessel)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="IMO/MMSI already exists"
        ) from exc
    await session.refresh(vessel)
    return _vessel_to_out(vessel)


@router.post(
    "/{vessel_id}/position",
    response_model=VesselPositionOut,
    status_code=status.HTTP_201_CREATED,
)
async def ingest_position(
    vessel_id: uuid.UUID,
    payload: VesselPositionCreate,
    session: AsyncSession = Depends(get_session),
    _current: User = Depends(get_current_user),
) -> VesselPositionOut:
    vessel = await session.get(Vessel, vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")

    pos = VesselPosition(
        vessel_id=vessel_id,
        lat=payload.lat,
        lon=payload.lon,
        sog_knots=payload.speed_over_ground,
        cog_deg=payload.course_over_ground,
        heading_deg=payload.heading,
        nav_status=payload.nav_status,
        source="AIS",
        recorded_at=payload.recorded_at or datetime.now(tz=timezone.utc),
    )
    session.add(pos)
    await session.commit()
    await session.refresh(pos)
    return _position_to_out(pos)


class CrewMember(BaseModel):
    id: str
    name: str
    rank: str
    nationality: str
    years_experience: int
    on_duty: bool


class MaintenanceItem(BaseModel):
    id: str
    title: str
    category: str   # engine | hull | navigation | safety | comms
    status: str     # scheduled | in_progress | completed | overdue
    due_date: datetime
    cost_estimate_usd: float
    notes: Optional[str] = None


_RANKS = [
    ("Master / Captain", 1),
    ("Chief Officer", 1),
    ("Second Officer", 1),
    ("Third Officer", 1),
    ("Chief Engineer", 1),
    ("Second Engineer", 1),
    ("Third Engineer", 1),
    ("Bosun", 1),
    ("AB Seaman", 3),
    ("Oiler", 2),
    ("Cook", 1),
    ("Steward", 1),
]
_NATIONALITIES = ["Azerbaijan", "Russia", "Turkey", "Iran", "Kazakhstan", "Turkmenistan", "Georgia"]
_FIRST_NAMES = [
    "Rashid", "Elnur", "Tural", "Vusal", "Aibek", "Murat", "Kamran", "Nijat", "Ilkin",
    "Ramin", "Sabir", "Farid", "Anar", "Orkhan", "Emil", "Javid", "Vugar", "Ruslan",
    "Sergei", "Dmitri", "Aleksey", "Bekzhan", "Nurlan", "Aslan",
]
_LAST_NAMES = [
    "Aliyev", "Mammadov", "Hasanov", "Quliyev", "Nurlanov", "Jafarov", "Babayev", "Karimov",
    "Ismayilov", "Hüseynov", "Rzayev", "Abbasov", "Ivanov", "Petrov", "Sokolov",
]


def _vessel_seed(vessel_id: uuid.UUID) -> int:
    return int(hashlib.md5(str(vessel_id).encode()).hexdigest()[:8], 16)


def _mock_crew(vessel_id: uuid.UUID) -> list[CrewMember]:
    rnd = _random.Random(_vessel_seed(vessel_id))
    out: list[CrewMember] = []
    idx = 0
    for rank, count in _RANKS:
        for _ in range(count):
            idx += 1
            name = f"{rnd.choice(_FIRST_NAMES)} {rnd.choice(_LAST_NAMES)}"
            out.append(CrewMember(
                id=f"crew-{vessel_id}-{idx}",
                name=name,
                rank=rank,
                nationality=rnd.choice(_NATIONALITIES),
                years_experience=rnd.randint(1, 25),
                on_duty=rnd.random() > 0.18,
            ))
    return out


def _mock_maintenance(vessel_id: uuid.UUID) -> list[MaintenanceItem]:
    rnd = _random.Random(_vessel_seed(vessel_id) ^ 0xA5)
    now = datetime.now(tz=timezone.utc)
    catalog = [
        ("Main engine overhaul",        "engine"),
        ("Hull cleaning + antifouling", "hull"),
        ("Lifeboat inspection",         "safety"),
        ("Radar calibration",           "navigation"),
        ("VHF radio service",           "comms"),
        ("Fire pump test",              "safety"),
        ("Propeller polish",            "hull"),
        ("Auxiliary genset service",    "engine"),
        ("ECDIS chart update",          "navigation"),
        ("Bilge alarm test",            "safety"),
    ]
    out: list[MaintenanceItem] = []
    for i, (title, cat) in enumerate(rnd.sample(catalog, k=rnd.randint(5, 8))):
        offset_d = rnd.randint(-30, 90)
        due = now + _timedelta(days=offset_d)
        if offset_d < -3:
            status = "completed"
        elif offset_d < 0:
            status = "overdue"
        elif offset_d < 7:
            status = "in_progress"
        else:
            status = "scheduled"
        out.append(MaintenanceItem(
            id=f"maint-{vessel_id}-{i}",
            title=title, category=cat, status=status,
            due_date=due,
            cost_estimate_usd=round(rnd.uniform(2_500, 95_000), 2),
            notes=None if rnd.random() > 0.5 else rnd.choice([
                "Yard scheduled at Baku drydock.",
                "Parts ordered ex-stock.",
                "Pending class society approval.",
                "Done in transit by chief engineer.",
            ]),
        ))
    out.sort(key=lambda m: m.due_date)
    return out


@router.get("/{vessel_id}/crew", response_model=List[CrewMember])
async def list_crew(
    vessel_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> List[CrewMember]:
    if not await session.get(Vessel, vessel_id):
        raise HTTPException(status_code=404, detail="Vessel not found")
    return _mock_crew(vessel_id)


@router.get("/{vessel_id}/maintenance", response_model=List[MaintenanceItem])
async def list_maintenance(
    vessel_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> List[MaintenanceItem]:
    if not await session.get(Vessel, vessel_id):
        raise HTTPException(status_code=404, detail="Vessel not found")
    return _mock_maintenance(vessel_id)


@router.get("/{vessel_id}/positions", response_model=List[VesselPositionOut])
async def list_positions(
    vessel_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
) -> List[VesselPositionOut]:
    stmt = (
        select(VesselPosition)
        .where(VesselPosition.vessel_id == vessel_id)
        .order_by(desc(VesselPosition.recorded_at))
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_position_to_out(p) for p in rows]
