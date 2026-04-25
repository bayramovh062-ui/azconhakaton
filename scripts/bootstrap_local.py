"""Bootstrap a local SQLite database for the NexusAZ backend.

Creates `nexusaz.db` (or whatever `DATABASE_URL` points at), runs
`Base.metadata.create_all`, then idempotently seeds 1 admin user, 3
vessels, 3 Baku-port berths, 2 bookings, 6 AIS positions, 1 ESG row.

Usage:  python scripts/bootstrap_local.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

# Make sure repo root is importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Prefer the project-local SQLite db file if not configured otherwise
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'nexusaz.db'}")

from sqlalchemy import select  # noqa: E402

from backend.auth.utils import hash_password  # noqa: E402
from backend.database import (  # noqa: E402
    AsyncSessionLocal,
    DATABASE_URL,
    close_engine,
    init_models,
)
from backend.models import (  # noqa: E402
    Berth,
    EsgMetric,
    PortBooking,
    User,
    Vessel,
    VesselPosition,
)


# Stable UUIDs so seed is idempotent and re-runs are safe
ADMIN_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
V1 = uuid.UUID("22222222-aaaa-4aaa-aaaa-000000000001")
V2 = uuid.UUID("22222222-aaaa-4aaa-aaaa-000000000002")
V3 = uuid.UUID("22222222-aaaa-4aaa-aaaa-000000000003")
B1 = uuid.UUID("33333333-bbbb-4bbb-bbbb-000000000001")
B2 = uuid.UUID("33333333-bbbb-4bbb-bbbb-000000000002")
B3 = uuid.UUID("33333333-bbbb-4bbb-bbbb-000000000003")
BK1 = uuid.UUID("44444444-cccc-4ccc-cccc-000000000001")
BK2 = uuid.UUID("44444444-cccc-4ccc-cccc-000000000002")


async def seed() -> None:
    now = datetime.now(tz=timezone.utc)
    async with AsyncSessionLocal() as session:
        # ---- Admin user ----
        existing_admin = (
            await session.execute(select(User).where(User.id == ADMIN_ID))
        ).scalar_one_or_none()
        if not existing_admin:
            session.add(
                User(
                    id=ADMIN_ID,
                    email="admin@nexusaz.io",
                    hashed_password=hash_password("Admin@123"),
                    full_name="NexusAZ Administrator",
                    role="admin",
                    is_active=True,
                )
            )
            print("[seed] admin user created (email=admin@nexusaz.io password=Admin@123)")
        else:
            print("[seed] admin user already exists")

        # ---- Vessels ----
        vessel_specs = [
            (V1, "IMO9456321", "423000100", "Caspian Pioneer", "tanker", "Azerbaijan",
             183.20, "Caspian Shipping Co."),
            (V2, "IMO9501234", "423000200", "Baku Star", "cargo", "Azerbaijan",
             145.00, "ASCO"),
            (V3, "IMO9612345", "273456789", "Volga Trader", "bulk", "Russia",
             159.50, "Volga-Don Logistics"),
        ]
        for vid, imo, mmsi, name, vtype, flag, length, op in vessel_specs:
            ex = await session.get(Vessel, vid)
            if ex:
                continue
            session.add(
                Vessel(
                    id=vid, imo=imo, mmsi=mmsi, name=name, vessel_type=vtype,
                    flag=flag, length_m=Decimal(str(length)), operator=op,
                    status="active",
                )
            )
        print("[seed] vessels ensured")

        # ---- Berths (Baku port ~40.3500N, 49.8700E) ----
        berth_specs = [
            (B1, "BAK-B1", "Baku Berth 1 - General Cargo", 40.3505, 49.8702,
             "general", "available", 200.00, 10.50),
            (B2, "BAK-B2", "Baku Berth 2 - Tanker Terminal", 40.3492, 49.8715,
             "liquid_bulk", "occupied", 220.00, 12.00),
            (B3, "BAK-B3", "Baku Berth 3 - Ro-Ro / Container", 40.3517, 49.8688,
             "container", "available", 180.00, 9.50),
        ]
        for bid, code, name, lat, lon, cargo, status, max_loa, max_draft in berth_specs:
            ex = await session.get(Berth, bid)
            if ex:
                continue
            session.add(
                Berth(
                    id=bid, code=code, name=name,
                    port_name="Baku International Sea Trade Port",
                    location_lat=lat, location_lon=lon,
                    max_loa_m=Decimal(str(max_loa)),
                    max_draft_m=Decimal(str(max_draft)),
                    cargo_type=cargo, status=status,
                )
            )
        print("[seed] berths ensured")

        await session.flush()

        # ---- Bookings ----
        booking_specs = [
            (BK1, V1, B2, now + timedelta(hours=6), now + timedelta(hours=30),
             "confirmed", "35,000 t crude oil - discharge operation", "NXZ-2025-0001"),
            (BK2, V2, B1, now + timedelta(hours=18), now + timedelta(hours=40),
             "scheduled", "Mixed general cargo from Aktau", "NXZ-2025-0002"),
        ]
        for bid, vid, berth_id, eta, etd, status, cargo, ref in booking_specs:
            ex = await session.get(PortBooking, bid)
            if ex:
                continue
            session.add(
                PortBooking(
                    id=bid, vessel_id=vid, berth_id=berth_id,
                    eta=eta, etd=etd, status=status,
                    cargo_description=cargo, booking_reference=ref,
                    created_by=ADMIN_ID,
                )
            )
        print("[seed] bookings ensured")

        # ---- Vessel positions (only seed if empty) ----
        any_pos = (
            await session.execute(select(VesselPosition).limit(1))
        ).scalar_one_or_none()
        if not any_pos:
            positions = [
                (V1, 40.2800, 49.8500, 12.40, 15.0, 14.0, now - timedelta(minutes=90)),
                (V1, 40.3100, 49.8580, 11.80, 20.0, 18.0, now - timedelta(minutes=60)),
                (V1, 40.3350, 49.8650, 8.20, 25.0, 23.0, now - timedelta(minutes=20)),
                (V2, 40.3600, 50.0500, 13.10, 270.0, 268.0, now - timedelta(minutes=120)),
                (V2, 40.3550, 49.9500, 12.60, 268.0, 267.0, now - timedelta(minutes=45)),
                (V3, 40.4200, 49.7800, 10.30, 135.0, 134.0, now - timedelta(minutes=30)),
            ]
            for vid, lat, lon, sog, cog, hdg, ts in positions:
                session.add(
                    VesselPosition(
                        vessel_id=vid, lat=lat, lon=lon,
                        sog_knots=Decimal(str(sog)),
                        cog_deg=Decimal(str(cog)),
                        heading_deg=Decimal(str(hdg)),
                        nav_status="under_way_using_engine",
                        source="AIS",
                        recorded_at=ts,
                    )
                )
            print(f"[seed] {len(positions)} vessel positions inserted")
        else:
            print("[seed] vessel positions already present")

        # ---- ESG metric ----
        any_esg = (
            await session.execute(select(EsgMetric).limit(1))
        ).scalar_one_or_none()
        if not any_esg:
            session.add(
                EsgMetric(
                    vessel_id=V1, booking_id=BK1,
                    period_start=now - timedelta(hours=24),
                    period_end=now,
                    fuel_consumed_t=Decimal("18.450"),
                    co2_emitted_kg=Decimal("57564.00"),
                    nox_emitted_kg=Decimal("1290.50"),
                    sox_emitted_kg=Decimal("95.20"),
                    waiting_time_hours=Decimal("1.20"),
                    distance_nm=Decimal("245.30"),
                    notes="Baseline voyage telemetry - pre-JIT optimization window.",
                )
            )
            print("[seed] esg metric inserted")
        else:
            print("[seed] esg metric already present")

        await session.commit()


async def main() -> int:
    print(f"[bootstrap] DATABASE_URL = {DATABASE_URL}")
    print("[bootstrap] creating tables ...")
    await init_models()
    print("[bootstrap] seeding ...")
    await seed()
    await close_engine()
    print("[bootstrap] DONE")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
