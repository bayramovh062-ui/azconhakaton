"""Bookings REST router."""

from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.auth.utils import get_current_user
from backend.database import get_session
from backend.models import Berth, PortBooking, User, Vessel

from .schemas import (
    BerthMini,
    BookingCreate,
    BookingOut,
    BookingUpdate,
    VesselMini,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _booking_to_out(b: PortBooking) -> BookingOut:
    return BookingOut(
        id=b.id,
        vessel_id=b.vessel_id,
        berth_id=b.berth_id,
        scheduled_arrival=b.eta,
        scheduled_departure=b.etd,
        actual_arrival=b.actual_arrival,
        actual_departure=b.actual_departure,
        cargo_type=b.cargo_description,
        booking_reference=b.booking_reference,
        status=b.status,
        created_at=b.created_at,
        updated_at=b.updated_at,
        berth=BerthMini.model_validate(b.berth) if b.berth else None,
        vessel=VesselMini.model_validate(b.vessel) if b.vessel else None,
    )


def _booking_query():
    return select(PortBooking).options(
        selectinload(PortBooking.berth),
        selectinload(PortBooking.vessel),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=List[BookingOut])
async def list_bookings(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    session: AsyncSession = Depends(get_session),
) -> List[BookingOut]:
    stmt = _booking_query()
    if status_filter:
        stmt = stmt.where(PortBooking.status == status_filter)
    stmt = stmt.order_by(PortBooking.eta.asc())
    rows = (await session.execute(stmt)).scalars().all()
    return [_booking_to_out(b) for b in rows]


@router.get("/vessel/{vessel_id}", response_model=List[BookingOut])
async def list_bookings_for_vessel(
    vessel_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> List[BookingOut]:
    stmt = (
        _booking_query()
        .where(PortBooking.vessel_id == vessel_id)
        .order_by(PortBooking.eta.desc())
    )
    rows = (await session.execute(stmt)).scalars().all()
    return [_booking_to_out(b) for b in rows]


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> BookingOut:
    stmt = _booking_query().where(PortBooking.id == booking_id)
    booking = (await session.execute(stmt)).scalar_one_or_none()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return _booking_to_out(booking)


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
async def create_booking(
    payload: BookingCreate,
    session: AsyncSession = Depends(get_session),
    current: User = Depends(get_current_user),
) -> BookingOut:
    vessel = await session.get(Vessel, payload.vessel_id)
    if not vessel:
        raise HTTPException(status_code=404, detail="Vessel not found")
    berth = await session.get(Berth, payload.berth_id)
    if not berth:
        raise HTTPException(status_code=404, detail="Berth not found")

    booking = PortBooking(
        vessel_id=payload.vessel_id,
        berth_id=payload.berth_id,
        eta=payload.scheduled_arrival,
        etd=payload.scheduled_departure,
        cargo_description=payload.cargo_type,
        booking_reference=payload.booking_reference,
        status="scheduled",
        created_by=current.id,
    )
    session.add(booking)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="Booking reference already exists"
        ) from exc

    stmt = _booking_query().where(PortBooking.id == booking.id)
    booking = (await session.execute(stmt)).scalar_one()
    return _booking_to_out(booking)


@router.patch("/{booking_id}", response_model=BookingOut)
async def update_booking(
    booking_id: uuid.UUID,
    payload: BookingUpdate,
    session: AsyncSession = Depends(get_session),
    _current: User = Depends(get_current_user),
) -> BookingOut:
    booking = await session.get(PortBooking, booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if payload.actual_arrival is not None:
        booking.actual_arrival = payload.actual_arrival
    if payload.actual_departure is not None:
        booking.actual_departure = payload.actual_departure
    if payload.status is not None:
        booking.status = payload.status

    await session.commit()

    stmt = _booking_query().where(PortBooking.id == booking_id)
    booking = (await session.execute(stmt)).scalar_one()
    return _booking_to_out(booking)
