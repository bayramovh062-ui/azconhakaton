# NexusAZ — FastAPI Backend

Async FastAPI backend for the NexusAZ Just-in-Time vessel arrival platform.

## Layout

```
backend/
├── main.py              # FastAPI app + lifespan + WebSocket + bg tasks
├── config.py            # pydantic-settings (.env)
├── database.py          # re-exports db.database (engine/session/Base)
├── models.py            # re-exports db.models (ORM)
├── auth/                # JWT login + current-user dependency
├── vessels/             # vessel CRUD + AIS position ingest
├── bookings/            # port booking CRUD
├── jit/                 # JIT engine (Haversine) + REST endpoints
├── esg/                 # ESG dashboard summary + daily series
├── websocket/           # ConnectionManager (broadcasts fleet status)
├── ais/                 # mock AIS simulator (5 vessels → Baku)
├── requirements.txt
├── .env.example
└── README.md
```

## Run

```powershell
# 1. Apply DB schema (Postgres + PostGIS must be running)
alembic -c db/alembic.ini upgrade head
psql $env:DATABASE_URL -f db/seed.sql

# 2. Install backend deps
pip install -r backend/requirements.txt

# 3. Copy env and edit secrets
copy backend/.env.example backend/.env

# 4. Run (from project root)
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000/docs for Swagger UI.

## Background tasks (started in `lifespan`)

| Task              | Period | Behavior                                                  |
| ----------------- | ------ | --------------------------------------------------------- |
| AIS simulator     | 10 s   | Moves 5 mock vessels toward Baku, persists `vessel_positions` |
| JIT broadcaster   | 5 s    | Computes fleet JIT status, broadcasts JSON over `/ws/fleet`   |

## Endpoints (high-level)

- `POST /auth/login`, `GET /auth/me`
- `GET/POST /vessels`, `GET /vessels/{id}`, `POST /vessels/{id}/position`, `GET /vessels/{id}/positions`
- `GET/POST/PATCH /bookings…`, `GET /bookings/vessel/{id}`
- `POST /jit/calculate`, `GET /jit/recommendations/{vessel_id}`, `GET /jit/fleet-status`
- `GET /esg/summary`, `GET /esg/daily?days=30`
- `WS /ws/fleet`

## Notes / mappings

- `bookings.scheduled_arrival/_departure/cargo_type` map to ORM
  `eta/etd/cargo_description`.
- JIT engine status values (`OPTIMAL`, `OVERSPEED`, `UNDERSPEED`,
  `BERTH_READY`) were added to the `jit_recommendations.status` CHECK
  constraint.
- Fuel saved is computed and returned in **liters**; persisted in tonnes
  (`fuel_savings_t`) using marine-fuel density 0.85 kg/L. ESG summary
  converts back for display.
- `backend/database.py` and `backend/models.py` re-export from `db/`,
  which remains the single source of truth.
