"""NexusAZ ORM models — portable across SQLite and PostgreSQL.

The production-spec PostGIS-backed schema lives in `db/models.py` and
`db/schema.sql`. To keep the local dev experience friction-free (no
PostGIS install required), the *backend runtime* uses these portable
models with plain ``lat`` / ``lon`` ``Float`` columns instead of
``Geometry(POINT, 4326)``. Spatial math (Haversine, bearings) is done
in Python anyway.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


# ---------------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'operator', 'analyst', 'viewer', 'owner', 'captain')",
            name="users_role_check",
        ),
        Index("ix_users_email", "email"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="operator")
    operator_company: Mapped[Optional[str]] = mapped_column(String(128))
    vessel_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("vessels.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    bookings: Mapped[List["PortBooking"]] = relationship(
        back_populates="creator",
        foreign_keys="PortBooking.created_by",
    )
    vessel: Mapped[Optional["Vessel"]] = relationship(
        "Vessel", foreign_keys=[vessel_id]
    )
    voyage_logs: Mapped[List["VoyageLog"]] = relationship(
        back_populates="author", foreign_keys="VoyageLog.author_id"
    )


# ---------------------------------------------------------------------------
# VESSELS
# ---------------------------------------------------------------------------

class Vessel(Base):
    __tablename__ = "vessels"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance', 'decommissioned')",
            name="vessels_status_check",
        ),
        CheckConstraint(
            "vessel_type IN ('cargo', 'tanker', 'container', 'bulk', "
            "'ro-ro', 'passenger', 'tug', 'fishing', 'other')",
            name="vessels_type_check",
        ),
        Index("ix_vessels_imo", "imo"),
        Index("ix_vessels_mmsi", "mmsi"),
        Index("ix_vessels_name", "name"),
        Index("ix_vessels_status", "status"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    imo: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    mmsi: Mapped[Optional[str]] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    call_sign: Mapped[Optional[str]] = mapped_column(String(16))
    vessel_type: Mapped[str] = mapped_column(String(64), nullable=False, default="cargo")
    flag: Mapped[Optional[str]] = mapped_column(String(64))
    length_m: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    beam_m: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    draft_m: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    gross_tonnage: Mapped[Optional[int]] = mapped_column(Integer)
    deadweight_t: Mapped[Optional[int]] = mapped_column(Integer)
    operator: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    positions: Mapped[List["VesselPosition"]] = relationship(
        back_populates="vessel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    bookings: Mapped[List["PortBooking"]] = relationship(
        back_populates="vessel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recommendations: Mapped[List["JitRecommendation"]] = relationship(
        back_populates="vessel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    esg_metrics: Mapped[List["EsgMetric"]] = relationship(
        back_populates="vessel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------------
# BERTHS
# ---------------------------------------------------------------------------

class Berth(Base):
    __tablename__ = "berths"
    __table_args__ = (
        CheckConstraint(
            "status IN ('available', 'occupied', 'reserved', 'maintenance', 'closed')",
            name="berths_status_check",
        ),
        Index("ix_berths_status", "status"),
        Index("ix_berths_location", "location_lat", "location_lon"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    port_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="Baku International Sea Trade Port",
    )
    location_lat: Mapped[float] = mapped_column(Float, nullable=False)
    location_lon: Mapped[float] = mapped_column(Float, nullable=False)
    max_loa_m: Mapped[Optional[float]] = mapped_column(Numeric(7, 2))
    max_draft_m: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    cargo_type: Mapped[Optional[str]] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    bookings: Mapped[List["PortBooking"]] = relationship(
        back_populates="berth",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------------
# PORT BOOKINGS
# ---------------------------------------------------------------------------

class PortBooking(Base):
    __tablename__ = "port_bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'in_progress', "
            "'completed', 'cancelled', 'delayed')",
            name="port_bookings_status_check",
        ),
        CheckConstraint("etd IS NULL OR etd >= eta", name="port_bookings_eta_etd_check"),
        Index("ix_port_bookings_vessel_id", "vessel_id"),
        Index("ix_port_bookings_berth_id", "berth_id"),
        Index("ix_port_bookings_eta", "eta"),
        Index("ix_port_bookings_status", "status"),
        Index("ix_port_bookings_vessel_eta", "vessel_id", "eta"),
        Index("ix_port_bookings_berth_eta", "berth_id", "eta"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    vessel_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False
    )
    berth_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("berths.id", ondelete="CASCADE"), nullable=False
    )
    eta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    etd: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actual_departure: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    cargo_description: Mapped[Optional[str]] = mapped_column(Text)
    booking_reference: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    created_by: Mapped[Optional[_uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    vessel: Mapped["Vessel"] = relationship(back_populates="bookings")
    berth: Mapped["Berth"] = relationship(back_populates="bookings")
    creator: Mapped[Optional["User"]] = relationship(
        back_populates="bookings", foreign_keys=[created_by]
    )
    recommendations: Mapped[List["JitRecommendation"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    esg_metrics: Mapped[List["EsgMetric"]] = relationship(
        back_populates="booking",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


# ---------------------------------------------------------------------------
# VESSEL POSITIONS (AIS) — lat/lon floats
# ---------------------------------------------------------------------------

class VesselPosition(Base):
    __tablename__ = "vessel_positions"
    __table_args__ = (
        CheckConstraint(
            "cog_deg IS NULL OR (cog_deg >= 0 AND cog_deg <= 360)",
            name="vessel_positions_cog_check",
        ),
        CheckConstraint(
            "heading_deg IS NULL OR (heading_deg >= 0 AND heading_deg <= 360)",
            name="vessel_positions_heading_check",
        ),
        Index("ix_vessel_positions_recorded_at", "recorded_at"),
        Index("ix_vessel_positions_vessel_recorded", "vessel_id", "recorded_at"),
        Index("ix_vessel_positions_latlon", "lat", "lon"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    vessel_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False
    )
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    sog_knots: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    cog_deg: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    heading_deg: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    nav_status: Mapped[Optional[str]] = mapped_column(String(48))
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="AIS")
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vessel: Mapped["Vessel"] = relationship(back_populates="positions")


# ---------------------------------------------------------------------------
# JIT RECOMMENDATIONS
# ---------------------------------------------------------------------------

class JitRecommendation(Base):
    __tablename__ = "jit_recommendations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'expired', 'applied', "
            "'OPTIMAL', 'OVERSPEED', 'UNDERSPEED', 'BERTH_READY')",
            name="jit_recommendations_status_check",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="jit_recommendations_confidence_check",
        ),
        Index("ix_jit_recommendations_vessel_id", "vessel_id"),
        Index("ix_jit_recommendations_booking_id", "booking_id"),
        Index("ix_jit_recommendations_issued_at", "issued_at"),
        Index("ix_jit_recommendations_status", "status"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    vessel_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False
    )
    booking_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("port_bookings.id", ondelete="CASCADE")
    )
    recommended_speed: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    recommended_eta: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fuel_savings_t: Mapped[Optional[float]] = mapped_column(Numeric(10, 3))
    co2_savings_kg: Mapped[Optional[float]] = mapped_column(Numeric(12, 2))
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(4, 3))
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    vessel: Mapped["Vessel"] = relationship(back_populates="recommendations")
    booking: Mapped[Optional["PortBooking"]] = relationship(
        back_populates="recommendations"
    )


# ---------------------------------------------------------------------------
# ESG METRICS
# ---------------------------------------------------------------------------

class EsgMetric(Base):
    __tablename__ = "esg_metrics"
    __table_args__ = (
        CheckConstraint(
            "period_end >= period_start", name="esg_metrics_period_check"
        ),
        Index("ix_esg_metrics_vessel_id", "vessel_id"),
        Index("ix_esg_metrics_booking_id", "booking_id"),
        Index("ix_esg_metrics_period", "period_start", "period_end"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    vessel_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("vessels.id", ondelete="CASCADE")
    )
    booking_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("port_bookings.id", ondelete="CASCADE")
    )
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fuel_consumed_t: Mapped[Optional[float]] = mapped_column(Numeric(12, 3))
    co2_emitted_kg: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    nox_emitted_kg: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    sox_emitted_kg: Mapped[Optional[float]] = mapped_column(Numeric(14, 2))
    waiting_time_hours: Mapped[Optional[float]] = mapped_column(Numeric(8, 2))
    distance_nm: Mapped[Optional[float]] = mapped_column(Numeric(10, 2))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vessel: Mapped[Optional["Vessel"]] = relationship(back_populates="esg_metrics")
    booking: Mapped[Optional["PortBooking"]] = relationship(back_populates="esg_metrics")


# ---------------------------------------------------------------------------
# VOYAGE LOG (captain notes, observations, incidents)
# ---------------------------------------------------------------------------

class VoyageLog(Base):
    __tablename__ = "voyage_logs"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('entry', 'observation', 'incident', 'fuel', 'eta_update')",
            name="voyage_logs_kind_check",
        ),
        Index("ix_voyage_logs_vessel_created", "vessel_id", "created_at"),
    )

    id: Mapped[_uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid.uuid4)
    vessel_id: Mapped[_uuid.UUID] = mapped_column(
        Uuid, ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False
    )
    author_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    booking_id: Mapped[Optional[_uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("port_bookings.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="entry")
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    vessel: Mapped["Vessel"] = relationship("Vessel", foreign_keys=[vessel_id])
    author: Mapped[Optional["User"]] = relationship(
        "User", back_populates="voyage_logs", foreign_keys=[author_id]
    )
    booking: Mapped[Optional["PortBooking"]] = relationship(
        "PortBooking", foreign_keys=[booking_id]
    )


__all__ = [
    "Base",
    "User",
    "Vessel",
    "Berth",
    "PortBooking",
    "VesselPosition",
    "JitRecommendation",
    "EsgMetric",
    "VoyageLog",
]
