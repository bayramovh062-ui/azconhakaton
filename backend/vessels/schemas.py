"""Vessel and AIS-position schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Vessels
# ---------------------------------------------------------------------------

class VesselCreate(BaseModel):
    mmsi: Optional[str] = Field(default=None, max_length=16)
    imo: Optional[str] = Field(default=None, max_length=16)
    name: str = Field(min_length=1, max_length=128)
    flag: Optional[str] = Field(default=None, max_length=64)
    vessel_type: str = Field(default="cargo", max_length=64)
    length_meters: Optional[float] = Field(default=None, ge=0)
    max_speed_knots: Optional[float] = Field(default=14.0, ge=0)
    operator: Optional[str] = Field(default=None, max_length=128)


class VesselOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    imo: Optional[str] = None
    mmsi: Optional[str] = None
    name: str
    flag: Optional[str] = None
    vessel_type: str
    length_meters: Optional[float] = None
    max_speed_knots: Optional[float] = None
    operator: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Vessel positions (AIS)
# ---------------------------------------------------------------------------

class VesselPositionCreate(BaseModel):
    vessel_id: Optional[uuid.UUID] = None
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    speed_over_ground: Optional[float] = Field(default=None, ge=0)
    course_over_ground: Optional[float] = Field(default=None, ge=0, le=360)
    heading: Optional[float] = Field(default=None, ge=0, le=360)
    nav_status: Optional[str] = None
    recorded_at: Optional[datetime] = None


class VesselPositionOut(BaseModel):
    id: int
    vessel_id: uuid.UUID
    lat: float
    lon: float
    speed_over_ground: Optional[float] = None
    course_over_ground: Optional[float] = None
    heading: Optional[float] = None
    nav_status: Optional[str] = None
    source: str
    recorded_at: datetime
    created_at: datetime
