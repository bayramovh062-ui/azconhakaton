"""Mock AIS data generator.

Simulates 5 vessels sailing toward Baku Port from random bearings and
distances (50–200 nm). On every `simulate_tick()` each vessel inches
closer to port and gets a small random perturbation in speed/heading.
"""

from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.models import Vessel, VesselPosition
from backend.vessels.schemas import VesselPositionCreate

# 1 degree of latitude ≈ 60 nautical miles
NM_PER_DEG_LAT = 60.0


def _nm_per_deg_lon(lat_deg: float) -> float:
    """Length of one degree of longitude (NM) at a given latitude."""
    return 60.0 * math.cos(math.radians(lat_deg))


@dataclass
class SimVessel:
    name: str
    lat: float
    lon: float
    speed: float        # knots
    course: float       # degrees, 0=N, 90=E
    db_id: Optional[uuid.UUID] = None
    imo: str = field(default_factory=lambda: f"SIM{random.randint(1000000, 9999999)}")
    mmsi: str = field(default_factory=lambda: str(random.randint(200_000_000, 799_999_999)))


class AISSimulator:
    """Maintains in-memory simulated vessels and produces position ticks."""

    def __init__(
        self,
        vessel_count: int = 5,
        port_lat: float = settings.BAKU_PORT_LAT,
        port_lon: float = settings.BAKU_PORT_LON,
    ) -> None:
        self.port_lat = port_lat
        self.port_lon = port_lon
        self.vessels: List[SimVessel] = [
            self._spawn_vessel(i) for i in range(vessel_count)
        ]

    # ------------------------------------------------------------------
    # Spawn / spatial helpers
    # ------------------------------------------------------------------

    def _spawn_vessel(self, idx: int) -> SimVessel:
        bearing_deg = random.uniform(0, 360)
        distance_nm = random.uniform(50, 200)
        bearing_rad = math.radians(bearing_deg)

        # Project from port outwards along bearing
        d_lat = (distance_nm * math.cos(bearing_rad)) / NM_PER_DEG_LAT
        d_lon = (distance_nm * math.sin(bearing_rad)) / max(
            _nm_per_deg_lon(self.port_lat), 1e-6
        )
        lat = self.port_lat + d_lat
        lon = self.port_lon + d_lon

        # Course pointing back toward port
        course = (bearing_deg + 180.0) % 360.0

        return SimVessel(
            name=f"NXZ-SIM-{idx + 1:02d}",
            lat=lat,
            lon=lon,
            speed=random.uniform(8.0, 13.0),
            course=course,
        )

    @staticmethod
    def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dlmb = math.radians(lon2 - lon1)
        x = math.sin(dlmb) * math.cos(phi2)
        y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlmb)
        return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0

    # ------------------------------------------------------------------
    # DB sync
    # ------------------------------------------------------------------

    async def ensure_db_vessels(self, session: AsyncSession) -> None:
        """Create matching `Vessel` rows the first time we run."""
        for sv in self.vessels:
            if sv.db_id is not None:
                continue
            existing = (
                await session.execute(select(Vessel).where(Vessel.imo == sv.imo))
            ).scalar_one_or_none()
            if existing:
                sv.db_id = existing.id
                continue
            v = Vessel(
                imo=sv.imo,
                mmsi=sv.mmsi,
                name=sv.name,
                vessel_type="cargo",
                flag="Simulated",
                length_m=140 + random.random() * 60,
                operator="NexusAZ Sim",
                status="active",
            )
            session.add(v)
            await session.flush()
            sv.db_id = v.id
        await session.commit()

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def simulate_tick(self, dt_seconds: float = 10.0) -> List[VesselPositionCreate]:
        """Advance every vessel by `dt_seconds` and return new positions."""
        out: List[VesselPositionCreate] = []
        now = datetime.now(tz=timezone.utc)

        for sv in self.vessels:
            # Steer toward port (always converge over time)
            target_course = self._bearing_deg(sv.lat, sv.lon, self.port_lat, self.port_lon)
            sv.course = (sv.course * 0.7 + target_course * 0.3) % 360.0

            # Random walk on speed (clamped 4..15)
            sv.speed = max(4.0, min(15.0, sv.speed + random.uniform(-0.5, 0.5)))

            # Move
            distance_nm = sv.speed * (dt_seconds / 3600.0)
            course_rad = math.radians(sv.course)
            d_lat = (distance_nm * math.cos(course_rad)) / NM_PER_DEG_LAT
            d_lon = (distance_nm * math.sin(course_rad)) / max(
                _nm_per_deg_lon(sv.lat), 1e-6
            )
            sv.lat += d_lat + random.uniform(-0.0002, 0.0002)
            sv.lon += d_lon + random.uniform(-0.0002, 0.0002)

            if sv.db_id is None:
                continue

            out.append(
                VesselPositionCreate(
                    vessel_id=sv.db_id,
                    lat=sv.lat,
                    lon=sv.lon,
                    speed_over_ground=round(sv.speed, 2),
                    course_over_ground=round(sv.course, 2),
                    heading=round(sv.course, 2),
                    nav_status="under_way_using_engine",
                    recorded_at=now,
                )
            )
        return out

    async def persist_tick(self, session: AsyncSession) -> int:
        """Run a tick and persist positions. Returns row count."""
        await self.ensure_db_vessels(session)
        positions = self.simulate_tick(dt_seconds=settings.AIS_TICK_SECONDS)
        for p in positions:
            session.add(
                VesselPosition(
                    vessel_id=p.vessel_id,
                    lat=p.lat,
                    lon=p.lon,
                    sog_knots=p.speed_over_ground,
                    cog_deg=p.course_over_ground,
                    heading_deg=p.heading,
                    nav_status=p.nav_status,
                    source="AIS-SIM",
                    recorded_at=p.recorded_at,
                )
            )
        await session.commit()
        return len(positions)


simulator = AISSimulator(vessel_count=5)
