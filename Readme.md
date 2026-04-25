## ⚓ AZMarine — Just-in-Time Vessel Arrival Intelligence

> **Caspian-focused maritime ops platform**
> Eliminates the *"Speed-to-Wait"* problem in port logistics by synchronising Baku Port berth availability with live vessel telemetry, then computing the optimal arrival speed for every inbound ship — saving fuel, cutting CO₂ and reducing port-basin congestion.

Built for the **AZCON Hackathon** as a full-stack production-sensible reference implementation.

---

## ✨ What's inside

A complete full-stack maritime SaaS with **6 role-based panels**:

| Role         | Lands on                | Sees                                                                                |
| ------------ | ----------------------- | ----------------------------------------------------------------------------------- |
| `admin`      | `/dashboard`            | Everything — global KPIs, all vessels, all panels                                    |
| `operator`   | `/dashboard`            | Operations console + Live Map + Bookings + JIT Tool + ESG                            |
| `analyst`    | `/dashboard`            | Read-mostly view focused on ESG analytics                                            |
| `viewer`     | `/dashboard`            | Read-only dashboard                                                                  |
| **`owner`**  | **`/owner`**            | Fleet-wide KPIs scoped to operator company, vessel table, savings trend chart        |
| **`captain`**| **`/captain`**          | Voyage cockpit: live JIT advisory + Accept/Apply/Reject, position submit, voyage log |

### Highlights

- **JIT engine** — Haversine distance, time-budget computation, speed clamping, status classification (`OPTIMAL` / `OVERSPEED` / `UNDERSPEED` / `BERTH_READY`), persistable recommendations.
- **Live fleet WebSocket** — `/ws/fleet` broadcasts every 5 s; React client auto-reconnects.
- **AIS simulator** — opt-in background task spawns 5 vessels approaching Baku Port and persists positions.
- **Notification center** — derived alert feed (JIT / SLA / infrastructure / telemetry gaps) with severity dots and acknowledge action.
- **Cmd-K command palette** — global search across navigation, vessels and bookings (keyboard-first).
- **Berth Gantt** — 14-day occupancy timeline, status-coloured bars, "now" line.
- **Compare vessels** — side-by-side stats for up to three vessels (JIT history, last/avg SOG, CO₂ saved).
- **Crew + Maintenance** — per-vessel deterministic mock with ranks, nationalities, due dates and USD cost estimates.
- **ESG dashboard** — fleet-wide CO₂ saved, optimal-arrival rate, daily fuel/CO₂ trend chart, "trees planted" equivalent.
- **Voyage log** — captain notes (entry / observation / incident / fuel / eta_update) and JIT acknowledgements auto-append entries.

---

## 🏗 Architecture

```
┌──────────────────────┐     ┌────────────────────────┐     ┌────────────────────────┐
│  React (Vite) + Tail │ ◀─▶ │  FastAPI async + JWT   │ ◀─▶ │  PostgreSQL + PostGIS  │
│  Leaflet • Recharts  │     │  asyncpg / aiosqlite   │     │  (or local SQLite)     │
│  WebSocket client    │     │  Alembic migrations    │     │  GeoAlchemy2           │
└──────────────────────┘     └────────────────────────┘     └────────────────────────┘
        ▲                              │
        │  /ws/fleet                   │  AIS sim (5 vessels)
        └──────────────────────────────┘  JIT broadcast (5 s)
```

---

## 📁 Repo layout

```
db/                           Canonical PostgreSQL + PostGIS schema, Alembic migration, SQL seed
backend/                      FastAPI app
  ├── auth/                   JWT login + role-based dependencies
  ├── vessels/                Vessel CRUD + AIS positions + crew + maintenance
  ├── bookings/               Port booking management
  ├── jit/                    JIT engine + recommendations
  ├── esg/                    ESG analytics endpoints
  ├── alerts/                 Derived alerts feed (+ /alerts/counts)
  ├── stats/                  Berth utilisation, top vessels, weather, activity
  ├── owner/                  Ship Owner panel API
  ├── captain/                Ship Captain cockpit API + voyage log
  ├── ais/                    Mock AIS simulator
  └── websocket/              Connection manager
frontend/                     React 19 + Vite + Tailwind
  ├── src/pages/              Dashboard, LiveMap, Fleet, VesselDetail, Bookings, Alerts,
  │                           EsgReport, JitTool, OwnerPanel, CaptainPanel, Compare, Settings, Login
  └── src/components/         Sidebar, TopHeader, CommandPalette, FleetMap, BerthGantt,
                              ActivityFeed, WeatherWidget, TopVessels, KpiCard, StatusBadge, ...
scripts/
  ├── bootstrap_local.py      Minimal SQLite seed
  └── bootstrap_rich.py       Full mock dataset (15 vessels, 8 berths, 25 bookings,
                              227 positions, 118 JIT recs, 30d ESG, 13 users, 25 voyage logs)
```

---

## 🚀 Quick start (zero-infra local SQLite)

```powershell
# 1. Backend deps
python -m pip install -r backend/requirements.txt aiosqlite

# 2. Seed DB with the rich mock dataset
python scripts/bootstrap_rich.py

# 3. Run the API
$env:DATABASE_URL = "sqlite+aiosqlite:///$($PWD.Path)\nexusaz.db"
$env:AZMARINE_ENABLE_AIS_SIM = "false"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765

# 4. Frontend (in another shell)
& "C:\Program Files\nodejs\npm.cmd" install --prefix frontend
& "C:\Program Files\nodejs\npm.cmd" run dev --prefix frontend -- --host 127.0.0.1 --port 5173
```

Open **http://127.0.0.1:5173** and login with one of the demo accounts:

| Role     | Email                          | Password       |
| -------- | ------------------------------ | -------------- |
| admin    | `admin@nexusaz.io`             | `Admin@123`    |
| operator | `operator@nexusaz.io`          | `Operator@123` |
| analyst  | `analyst@nexusaz.io`           | `Analyst@123`  |
| viewer   | `viewer@nexusaz.io`            | `Viewer@123`   |
| owner    | `owner@socar.az`               | `Owner@123`    |
| owner    | `owner@asco.az`                | `Owner@123`    |
| owner    | `owner@caspian.az`             | `Owner@123`    |
| owner    | `owner@kazmor.kz`              | `Owner@123`    |
| captain  | `captain.pioneer@nexusaz.io`   | `Captain@123`  |
| captain  | `captain.bakustar@nexusaz.io`  | `Captain@123`  |
| captain  | `captain.khazri@nexusaz.io`    | `Captain@123`  |
| captain  | `captain.aktau@nexusaz.io`     | `Captain@123`  |
| captain  | `captain.absheron@nexusaz.io`  | `Captain@123`  |

> Press **`Ctrl/⌘ + K`** anywhere for the global command palette.

---

## 🐘 Production deployment (PostgreSQL + PostGIS)

```bash
# Postgres + PostGIS must be running with a DB called azmarine
alembic -c db/alembic.ini upgrade head
psql "$DATABASE_URL" -f db/seed.sql

AZMARINE_DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/azmarine \
  uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

The `db/` package is the canonical schema (PostGIS `POINT/4326` geometry, GIST indexes, time-series + spatial-temporal composite indexes, CHECK constraints for enum-like statuses, `gen_random_uuid()` server defaults, automatic `updated_at` trigger). The `backend/` runtime mirrors the schema with portable `lat`/`lon` floats so it works on SQLite for dev and Postgres for prod.

---

## 🛠 Tech stack

| Layer            | Choice                                                                   |
| ---------------- | ------------------------------------------------------------------------ |
| API              | **FastAPI** (async) + **SQLAlchemy 2.0** + **Alembic**                   |
| Auth             | **JWT** (python-jose) + **bcrypt** (passlib) — role-based deps           |
| DB drivers       | **asyncpg** (Postgres) / **aiosqlite** (local dev)                       |
| Spatial          | **PostGIS 3.x** + **GeoAlchemy2** (POINT / 4326, GIST indexes)           |
| Realtime         | Native **WebSocket** (`/ws/fleet`) + auto-reconnect                      |
| Frontend         | **React 19** + **Vite** + **Tailwind CSS** + **React Router**            |
| Charts / maps    | **Recharts** + **react-leaflet** (CartoDB Dark Matter tiles)             |
| Icons            | **lucide-react**                                                         |
| Fonts            | Orbitron (display) • Inter (body) • JetBrains Mono (numbers)             |

---

## 📊 Impact metrics (modelled)

- **Fuel savings**: up to **~18 %** per voyage at typical Caspian transit speeds.
- **Emissions**: direct reduction in Maritime Carbon Intensity Indicator (CII) ratings.
- **Port efficiency**: **~30 %** reduction in port-basin anchoring/congestion time.

These are the numbers the JIT engine reproduces in the demo with the rich mock dataset.

---

## 🔐 Security model

- All API calls (except `POST /auth/login`) require **`Authorization: Bearer <jwt>`**.
- Passwords hashed with **bcrypt**.
- Role-aware routing both **server-side** (FastAPI dependencies) and **client-side** (sidebar + redirect).
- Captains can only mutate **their own vessel**; owners can only see vessels of **their operator company** (admin override available via query param for QA).

---

## 👥 Team

Built for the **AZCON Hackathon**.

> *AZMarine — Navigating the Future of Sustainable Shipping for the Caspian.*