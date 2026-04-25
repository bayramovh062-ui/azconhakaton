"""Core Just-in-Time arrival recommendation engine."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import TypedDict

from backend.config import settings


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Mean Earth radius in nautical miles (NM). 6371.0088 km / 1.852 km/NM.
EARTH_RADIUS_NM = 3440.065

MIN_SAFE_SPEED = 4.0  # knots — below this a vessel loses steerage
DEFAULT_MAX_SPEED = 14.0
SPEED_TOLERANCE = 1.0  # knots — band considered "OPTIMAL"


class JITResult(TypedDict):
    distance_nm: float
    time_available_hours: float
    recommended_speed: float
    current_speed: float
    status: str
    fuel_saved_liters: float
    co2_saved_kg: float


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    )
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return EARTH_RADIUS_NM * c


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class JITEngine:
    """Stateless calculator producing a JIT recommendation."""

    def calculate(
        self,
        vessel_lat: float,
        vessel_lon: float,
        current_speed: float,
        scheduled_arrival: datetime,
        port_lat: float = settings.BAKU_PORT_LAT,
        port_lon: float = settings.BAKU_PORT_LON,
        max_speed: float = DEFAULT_MAX_SPEED,
    ) -> JITResult:
        # 1. Distance
        distance_nm = haversine_nm(vessel_lat, vessel_lon, port_lat, port_lon)

        # 2. Time budget
        if scheduled_arrival.tzinfo is None:
            scheduled_arrival = scheduled_arrival.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        time_available_hours = (scheduled_arrival - now).total_seconds() / 3600.0

        # 3. Berth ready / overdue
        if time_available_hours <= 0:
            return JITResult(
                distance_nm=round(distance_nm, 3),
                time_available_hours=round(time_available_hours, 3),
                recommended_speed=round(min(max_speed, max(MIN_SAFE_SPEED, current_speed)), 2),
                current_speed=round(current_speed, 2),
                status="BERTH_READY",
                fuel_saved_liters=0.0,
                co2_saved_kg=0.0,
            )

        # 4. Required average speed
        if distance_nm <= 0.001:
            recommended_speed = MIN_SAFE_SPEED
        else:
            recommended_speed = distance_nm / time_available_hours

        # 5. Clamp to safe operational band
        recommended_speed = max(MIN_SAFE_SPEED, min(recommended_speed, max_speed))

        # 6. Status classification
        delta = current_speed - recommended_speed
        if abs(delta) <= SPEED_TOLERANCE:
            status = "OPTIMAL"
        elif delta > SPEED_TOLERANCE:
            status = "OVERSPEED"
        else:
            status = "UNDERSPEED"

        # 7. Fuel saved by NOT overspeeding
        excess_speed = max(0.0, current_speed - recommended_speed)
        fuel_saved_liters = (
            excess_speed * distance_nm * settings.FUEL_CONSUMPTION_RATE
        )

        # 8. CO2 saved
        co2_saved_kg = fuel_saved_liters * settings.CO2_PER_LITER

        return JITResult(
            distance_nm=round(distance_nm, 3),
            time_available_hours=round(time_available_hours, 3),
            recommended_speed=round(recommended_speed, 2),
            current_speed=round(current_speed, 2),
            status=status,
            fuel_saved_liters=round(fuel_saved_liters, 3),
            co2_saved_kg=round(co2_saved_kg, 3),
        )


# A module-level singleton is convenient and stateless.
jit_engine = JITEngine()
