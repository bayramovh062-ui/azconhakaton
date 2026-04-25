"""Bootstrap a *rich* SQLite dataset for NexusAZ.

Wipes the DB and seeds:
  * 4 users (admin, operator, analyst, viewer)
  * 8 berths around Baku Port
  * 15 vessels (Caspian-realistic mix of operators/types)
  * 25 port bookings spanning past 21d → next 14d (mix of statuses)
  * ~250 AIS positions covering 30 days of history
  * ~120 JIT recommendations across 30 days
  * 30 daily ESG metric rows

Run:  python scripts/bootstrap_rich.py
"""

from __future__ import annotations

import asyncio
import math
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{ROOT / 'nexusaz.db'}")

from sqlalchemy import delete, select  # noqa: E402

from backend.auth.utils import hash_password  # noqa: E402
from backend.database import (  # noqa: E402
    AsyncSessionLocal,
    DATABASE_URL,
    close_engine,
    init_models,
    reset_models,
)
from backend.models import (  # noqa: E402
    Berth,
    EsgMetric,
    JitRecommendation,
    PortBooking,
    User,
    Vessel,
    VesselPosition,
    VoyageLog,
)

random.seed(42)  # deterministic re-runs


# --------------------------------------------------------------------------- #
# Reference data                                                              #
# --------------------------------------------------------------------------- #

PORT_LAT, PORT_LON = 40.3500, 49.8700
NM_PER_DEG_LAT = 60.0


def _nm_per_deg_lon(lat):
    return 60.0 * math.cos(math.radians(lat))


def haversine_nm(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (
        math.sin(math.radians(lat2 - lat1) / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    )
    return 3440.065 * 2 * math.asin(min(1.0, math.sqrt(a)))


# Users — admin, operator, analyst, viewer + ship owners + ship captains.
# (id, email, password, full_name, role, operator_company, vessel_suffix)
USERS = [
    ("11111111-1111-1111-1111-111111111111", "admin@nexusaz.io",       "Admin@123",    "NexusAZ Admin",          "admin",    None,                    None),
    ("11111111-1111-1111-1111-111111111112", "operator@nexusaz.io",    "Operator@123", "Operations Lead",        "operator", None,                    None),
    ("11111111-1111-1111-1111-111111111113", "analyst@nexusaz.io",     "Analyst@123",  "Sustainability Analyst", "analyst",  None,                    None),
    ("11111111-1111-1111-1111-111111111114", "viewer@nexusaz.io",      "Viewer@123",   "Read-Only Viewer",       "viewer",   None,                    None),
    # Ship owners — scoped to operator companies
    ("11111111-1111-1111-1111-111111111201", "owner@socar.az",         "Owner@123",    "SOCAR Marine — Fleet Director",        "owner", "SOCAR Marine",          None),
    ("11111111-1111-1111-1111-111111111202", "owner@asco.az",          "Owner@123",    "ASCO — Fleet Director",                 "owner", "ASCO",                  None),
    ("11111111-1111-1111-1111-111111111203", "owner@caspian.az",       "Owner@123",    "Caspian Shipping Co. — CEO",            "owner", "Caspian Shipping Co.",  None),
    ("11111111-1111-1111-1111-111111111204", "owner@kazmor.kz",        "Owner@123",    "KazMorTransFlot — COO",                 "owner", "KazMorTransFlot",       None),
    # Ship captains — pinned to a specific vessel
    ("11111111-1111-1111-1111-111111111301", "captain.pioneer@nexusaz.io",  "Captain@123", "Capt. Rashid Aliyev",    "captain", "Caspian Shipping Co.", "01"),
    ("11111111-1111-1111-1111-111111111302", "captain.bakustar@nexusaz.io", "Captain@123", "Capt. Elnur Mammadov",   "captain", "ASCO",                 "02"),
    ("11111111-1111-1111-1111-111111111303", "captain.khazri@nexusaz.io",   "Captain@123", "Capt. Tural Hasanov",    "captain", "SOCAR Marine",         "04"),
    ("11111111-1111-1111-1111-111111111304", "captain.aktau@nexusaz.io",    "Captain@123", "Capt. Aibek Nurlanov",   "captain", "KazMorTransFlot",      "09"),
    ("11111111-1111-1111-1111-111111111305", "captain.absheron@nexusaz.io", "Captain@123", "Capt. Vusal Quliyev",    "captain", "SOCAR Marine",         "15"),
]

# 8 berths
BERTHS = [
    # (id_suffix, code, name, lat_off, lon_off, cargo, status, max_loa, max_draft)
    ("01", "BAK-B1", "Berth 1 — General Cargo",      0.0005,  0.0002, "general",     "available",   200, 10.5),
    ("02", "BAK-B2", "Berth 2 — Tanker Terminal",   -0.0008,  0.0015, "liquid_bulk", "occupied",    220, 12.0),
    ("03", "BAK-B3", "Berth 3 — Ro-Ro / Container",  0.0017, -0.0012, "container",   "available",   180, 9.5),
    ("04", "BAK-B4", "Berth 4 — Dry Bulk",           0.0028,  0.0023, "dry_bulk",    "occupied",    210, 11.0),
    ("05", "BAK-B5", "Berth 5 — Container",         -0.0021, -0.0028, "container",   "available",   240, 12.5),
    ("06", "BAK-B6", "Berth 6 — Ferry / Ro-Ro",      0.0040,  0.0009, "ro-ro",       "reserved",    160, 7.0),
    ("07", "BAK-B7", "Berth 7 — Crude Oil",         -0.0036, -0.0006, "liquid_bulk", "available",   260, 13.0),
    ("08", "BAK-B8", "Berth 8 — Specialised LNG",    0.0009, -0.0042, "lng",         "maintenance", 280, 13.5),
]

# 15 vessels (a realistic Caspian fleet)
# (id_suffix, imo, mmsi, name, type, flag, length_m, operator)
VESSELS = [
    ("01", "IMO9456321", "423000100", "Caspian Pioneer",  "tanker",    "Azerbaijan", 183.20, "Caspian Shipping Co."),
    ("02", "IMO9501234", "423000200", "Baku Star",        "cargo",     "Azerbaijan", 145.00, "ASCO"),
    ("03", "IMO9612345", "273456789", "Volga Trader",     "bulk",      "Russia",     159.50, "Volga-Don Logistics"),
    ("04", "IMO9701224", "423000301", "Khazri Spirit",    "tanker",    "Azerbaijan", 172.60, "SOCAR Marine"),
    ("05", "IMO9802211", "271111111", "Anatolian Bridge", "ro-ro",     "Turkey",     162.40, "DenizCo"),
    ("06", "IMO9510002", "273100200", "Astrakhan",        "container", "Russia",     189.10, "Caspar Lines"),
    ("07", "IMO9633400", "422998877", "Azerstar 7",       "tanker",    "Iran",       155.80, "NITC Caspian"),
    ("08", "IMO9650011", "273654321", "Saratov Glory",    "bulk",      "Russia",     148.30, "Volgotanker"),
    ("09", "IMO9712345", "457123456", "Aktau Pioneer",    "container", "Kazakhstan", 178.00, "KazMorTransFlot"),
    ("10", "IMO9888001", "440112233", "Turkmen Wave",     "tanker",    "Turkmenistan", 167.20, "Turkmen Sea Lines"),
    ("11", "IMO9900100", "423000402", "Bibi-Heybat",      "tug",       "Azerbaijan",  38.00, "Port Tug Services"),
    ("12", "IMO9450018", "271877766", "Ankara Trader",    "cargo",     "Turkey",     134.60, "DenizCo"),
    ("13", "IMO9433201", "457999100", "Baltic Caspian",   "container", "Kazakhstan", 192.50, "KazMorTransFlot"),
    ("14", "IMO9777123", "422111222", "Persian Pearl",    "passenger", "Iran",       138.00, "Iran Caspian Shipping"),
    ("15", "IMO9555010", "423000999", "Absheron Star",    "tanker",    "Azerbaijan", 198.40, "SOCAR Marine"),
]


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def vid(suffix):     return uuid.UUID(f"22222222-aaaa-4aaa-aaaa-0000000000{suffix}")
def bid(suffix):     return uuid.UUID(f"33333333-bbbb-4bbb-bbbb-0000000000{suffix}")
def book_id(idx):    return uuid.UUID(f"44444444-cccc-4ccc-cccc-{idx:012d}")
def jit_id(idx):     return uuid.UUID(f"55555555-dddd-4ddd-dddd-{idx:012d}")
def esg_id(idx):     return uuid.UUID(f"66666666-eeee-4eee-eeee-{idx:012d}")


def offset(lat0, lon0, distance_nm, bearing_deg):
    rad = math.radians(bearing_deg)
    d_lat = (distance_nm * math.cos(rad)) / NM_PER_DEG_LAT
    d_lon = (distance_nm * math.sin(rad)) / max(_nm_per_deg_lon(lat0), 1e-6)
    return lat0 + d_lat, lon0 + d_lon


# --------------------------------------------------------------------------- #
# Seed                                                                        #
# --------------------------------------------------------------------------- #

async def wipe(session):
    print("[wipe] dropping all rows ...")
    await session.execute(delete(JitRecommendation))
    await session.execute(delete(EsgMetric))
    await session.execute(delete(VesselPosition))
    await session.execute(delete(PortBooking))
    await session.execute(delete(Berth))
    await session.execute(delete(Vessel))
    await session.execute(delete(User))
    await session.commit()


async def seed():
    now = datetime.now(tz=timezone.utc)

    async with AsyncSessionLocal() as session:
        await wipe(session)

        # Users
        for uid, email, pw, name, role, company, v_suffix in USERS:
            session.add(User(
                id=uuid.UUID(uid),
                email=email,
                hashed_password=hash_password(pw),
                full_name=name,
                role=role,
                operator_company=company,
                vessel_id=vid(v_suffix) if v_suffix else None,
                is_active=True,
            ))
        print(f"[seed] {len(USERS)} users (admin/operator/analyst/viewer/owner/captain)")

        # Berths
        for suffix, code, name, lat_off, lon_off, cargo, status, max_loa, max_draft in BERTHS:
            session.add(Berth(
                id=bid(suffix),
                code=code,
                name=name,
                port_name="Baku International Sea Trade Port",
                location_lat=PORT_LAT + lat_off,
                location_lon=PORT_LON + lon_off,
                max_loa_m=Decimal(str(max_loa)),
                max_draft_m=Decimal(str(max_draft)),
                cargo_type=cargo,
                status=status,
            ))
        print(f"[seed] {len(BERTHS)} berths")

        # Vessels
        vstatus_choices = ["active"] * 12 + ["maintenance", "inactive", "active"]
        for i, (suffix, imo, mmsi, name, vtype, flag, length, op) in enumerate(VESSELS):
            session.add(Vessel(
                id=vid(suffix),
                imo=imo, mmsi=mmsi, name=name, vessel_type=vtype,
                flag=flag, length_m=Decimal(str(length)),
                beam_m=Decimal(str(round(length * 0.16, 2))),
                draft_m=Decimal(str(round(random.uniform(7, 12), 2))),
                gross_tonnage=int(length * 200 + random.randint(-2000, 2000)),
                deadweight_t=int(length * 320 + random.randint(-3000, 3000)),
                operator=op,
                status=vstatus_choices[i % len(vstatus_choices)],
            ))
        print(f"[seed] {len(VESSELS)} vessels")

        await session.flush()

        # Bookings — 25 mixed
        cargo_descs = [
            "35,000 t crude oil — discharge",
            "Mixed general cargo from Aktau",
            "Container shuttle from Türkmenbaşy",
            "20,000 t grain (export)",
            "Iron ore — bulk discharge",
            "Steel coils & project cargo",
            "Diesel fuel — bunkering",
            "Ro-Ro vehicles for Iran",
            "LNG bunkering operation",
            "Mixed reefer containers",
        ]
        BOOKINGS = []
        for i in range(25):
            v_idx = i % len(VESSELS)
            b_idx = i % len(BERTHS)
            # 10 past, 5 ongoing, 10 future
            if i < 10:
                eta = now - timedelta(days=random.randint(2, 21), hours=random.randint(0, 12))
                etd = eta + timedelta(hours=random.randint(20, 60))
                aa = eta + timedelta(minutes=random.randint(-90, 120))
                ad = etd + timedelta(minutes=random.randint(-30, 90))
                status = random.choice(["completed"] * 4 + ["cancelled"])
                if status == "cancelled":
                    aa = ad = None
            elif i < 15:
                eta = now - timedelta(hours=random.randint(2, 18))
                etd = now + timedelta(hours=random.randint(6, 30))
                aa = eta + timedelta(minutes=random.randint(0, 90))
                ad = None
                status = "in_progress"
            else:
                eta = now + timedelta(hours=random.randint(2, 14 * 24))
                etd = eta + timedelta(hours=random.randint(20, 60))
                aa = ad = None
                status = random.choice(["scheduled"] * 3 + ["confirmed", "delayed"])

            BOOKINGS.append((
                book_id(i + 1),
                vid(VESSELS[v_idx][0]),
                bid(BERTHS[b_idx][0]),
                eta, etd, aa, ad,
                status,
                random.choice(cargo_descs),
                f"NXZ-2025-{i + 1:04d}",
            ))

        for bk_id, v, b, eta, etd, aa, ad, status, cargo, ref in BOOKINGS:
            session.add(PortBooking(
                id=bk_id,
                vessel_id=v, berth_id=b,
                eta=eta, etd=etd,
                actual_arrival=aa, actual_departure=ad,
                status=status,
                cargo_description=cargo,
                booking_reference=ref,
                created_by=uuid.UUID(USERS[0][0]),
            ))
        print(f"[seed] {len(BOOKINGS)} bookings")

        # Vessel positions — last 30 days, ~16 active vessels worth
        positions_count = 0
        for i, (suffix, *_rest) in enumerate(VESSELS):
            v_uuid = vid(suffix)
            # generate a curve approaching the port over `hist_hours` random hours
            hist_hours = random.randint(20, 60)
            samples = random.randint(8, 20)
            # spawn point
            initial_distance = random.uniform(40, 220)
            bearing = random.uniform(0, 360)
            lat0, lon0 = offset(PORT_LAT, PORT_LON, initial_distance, bearing)

            for s in range(samples):
                fraction = s / max(1, samples - 1)
                # moves toward port, with noise
                lat = lat0 + (PORT_LAT - lat0) * fraction + random.uniform(-0.01, 0.01)
                lon = lon0 + (PORT_LON - lon0) * fraction + random.uniform(-0.01, 0.01)
                ts = now - timedelta(hours=hist_hours * (1 - fraction)) - timedelta(minutes=random.randint(0, 20))
                sog = max(4.0, min(15.0, random.gauss(11.5, 1.4)))
                cog = (bearing + 180 + random.uniform(-15, 15)) % 360
                session.add(VesselPosition(
                    vessel_id=v_uuid,
                    lat=lat, lon=lon,
                    sog_knots=Decimal(f"{sog:.2f}"),
                    cog_deg=Decimal(f"{cog:.2f}"),
                    heading_deg=Decimal(f"{cog:.2f}"),
                    nav_status="under_way_using_engine",
                    source="AIS",
                    recorded_at=ts,
                ))
                positions_count += 1
        print(f"[seed] {positions_count} vessel positions")

        # JIT recommendations — 30 days, ~4/day
        rec_count = 0
        statuses_pool = ["OPTIMAL"] * 5 + ["OVERSPEED"] * 3 + ["UNDERSPEED"] * 2
        for d in range(30):
            day_anchor = now - timedelta(days=d)
            for _ in range(random.randint(2, 6)):
                v_idx = random.randint(0, len(VESSELS) - 1)
                bk_idx = random.randint(0, len(BOOKINGS) - 1)
                v_uuid = vid(VESSELS[v_idx][0])
                bk_uuid = book_id(bk_idx + 1)
                status = random.choice(statuses_pool)
                rec_speed = round(random.uniform(8, 13), 2)
                fuel_l = round(random.uniform(0, 25) if status == "OVERSPEED" else random.uniform(0, 4), 2)
                co2 = round(fuel_l * 2.68, 2)
                tonnes = round(fuel_l * 0.00085, 4)
                ts = day_anchor - timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
                session.add(JitRecommendation(
                    id=jit_id(rec_count + 1),
                    vessel_id=v_uuid,
                    booking_id=bk_uuid,
                    recommended_speed=Decimal(str(rec_speed)),
                    recommended_eta=ts + timedelta(hours=random.randint(2, 12)),
                    fuel_savings_t=Decimal(str(tonnes)),
                    co2_savings_kg=Decimal(str(co2)),
                    confidence=Decimal(str(round(random.uniform(0.7, 0.99), 3))),
                    rationale=f"distance_nm={round(random.uniform(20,200),1)}; "
                              f"time_available_hours={round(random.uniform(2,18),1)}; "
                              f"current_speed={round(rec_speed + random.uniform(-3,3),2)}; "
                              f"recommended_speed={rec_speed}; "
                              f"fuel_saved_liters={fuel_l}; "
                              f"co2_saved_kg={co2}",
                    status=status,
                    issued_at=ts,
                ))
                rec_count += 1
        print(f"[seed] {rec_count} JIT recommendations")

        # ESG metrics — daily aggregates for 30 days
        for d in range(30):
            day_start = (now - timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(hours=23, minutes=59)
            session.add(EsgMetric(
                id=esg_id(d + 1),
                vessel_id=vid(VESSELS[d % len(VESSELS)][0]),
                period_start=day_start,
                period_end=day_end,
                fuel_consumed_t=Decimal(str(round(random.uniform(8, 30), 3))),
                co2_emitted_kg=Decimal(str(round(random.uniform(25000, 90000), 2))),
                nox_emitted_kg=Decimal(str(round(random.uniform(600, 1800), 2))),
                sox_emitted_kg=Decimal(str(round(random.uniform(40, 140), 2))),
                waiting_time_hours=Decimal(str(round(random.uniform(0, 6), 2))),
                distance_nm=Decimal(str(round(random.uniform(80, 320), 2))),
                notes=f"Day -{d} aggregate",
            ))
        print("[seed] 30 daily ESG rows")

        # Voyage logs for captain-owned vessels (pre-populate so the panel isn't empty)
        log_count = 0
        for uid, email, pw, name, role, company, v_suffix in USERS:
            if role != "captain" or not v_suffix:
                continue
            v_uuid = vid(v_suffix)
            seeds = [
                ("entry",       f"Departed Baku roads, course set toward port. — {name}"),
                ("observation", "Sea state 2, wind ENE 12 kn. Visibility good."),
                ("fuel",        "Bunker remaining 240 t. Burn rate within plan."),
                ("eta_update",  "Reduced speed to align with berth slot per JIT advisory."),
                ("observation", "Crew briefed on JIT optimization — comms with port control nominal."),
            ]
            for hours_ago, (kind, text) in enumerate(seeds):
                session.add(VoyageLog(
                    vessel_id=v_uuid,
                    author_id=uuid.UUID(uid),
                    kind=kind,
                    note=text,
                    created_at=now - timedelta(hours=hours_ago * 5 + random.randint(0, 60)),
                ))
                log_count += 1
        print(f"[seed] {log_count} voyage logs")

        await session.commit()


async def main():
    print(f"[bootstrap-rich] DATABASE_URL = {DATABASE_URL}")
    print("[bootstrap-rich] resetting schema (drop + create) ...")
    await reset_models()
    await seed()
    await close_engine()
    print("[bootstrap-rich] DONE")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
