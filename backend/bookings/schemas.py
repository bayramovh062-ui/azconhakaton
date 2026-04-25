"""Booking schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BookingCreate(BaseModel):
    vessel_id: uuid.UUID
    berth_id: uuid.UUID
    scheduled_arrival: datetime
    scheduled_departure: Optional[datetime] = None
    cargo_type: Optional[str] = Field(default=None, max_length=2048)
    booking_reference: Optional[str] = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def _check_window(self) -> "BookingCreate":
        if self.scheduled_departure and self.scheduled_departure < self.scheduled_arrival:
            raise ValueError("scheduled_departure must be >= scheduled_arrival")
        return self


class BookingUpdate(BaseModel):
    actual_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    status: Optional[str] = Field(default=None, max_length=32)


class BerthMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    port_name: str
    status: str


class VesselMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    vessel_type: str


class BookingOut(BaseModel):
    id: uuid.UUID
    vessel_id: uuid.UUID
    berth_id: uuid.UUID
    scheduled_arrival: datetime
    scheduled_departure: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None
    actual_departure: Optional[datetime] = None
    cargo_type: Optional[str] = None
    booking_reference: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    berth: Optional[BerthMini] = None
    vessel: Optional[VesselMini] = None
