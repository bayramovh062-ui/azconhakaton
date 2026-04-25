-- =====================================================================
-- NexusAZ — Just-in-Time Vessel Arrival Intelligence Platform
-- PostgreSQL 15+ / PostGIS 3.x initialization script
-- =====================================================================
-- This script is idempotent-friendly (uses IF NOT EXISTS where possible)
-- and is safe to run on a fresh database. It defines:
--   * Required extensions
--   * Enum-like CHECK constraints
--   * Core entities: users, vessels, berths, port_bookings,
--                    vessel_positions, jit_recommendations, esg_metrics
--   * Indexes for spatial + time-series + booking lookups
-- =====================================================================

-- ---------- EXTENSIONS ------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "postgis";    -- spatial types & indexes
CREATE EXTENSION IF NOT EXISTS "btree_gist"; -- composite spatial+btree GIST

-- ---------- USERS -----------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(32)  NOT NULL DEFAULT 'operator',
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT users_role_check
        CHECK (role IN ('admin', 'operator', 'analyst', 'viewer'))
);

CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- ---------- VESSELS ---------------------------------------------------
CREATE TABLE IF NOT EXISTS vessels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    imo             VARCHAR(16)  NOT NULL UNIQUE,   -- IMO number
    mmsi            VARCHAR(16)  UNIQUE,            -- AIS MMSI
    name            VARCHAR(128) NOT NULL,
    call_sign       VARCHAR(16),
    vessel_type     VARCHAR(64)  NOT NULL DEFAULT 'cargo',
    flag            VARCHAR(64),
    length_m        NUMERIC(7,2),
    beam_m          NUMERIC(7,2),
    draft_m         NUMERIC(6,2),
    gross_tonnage   INTEGER,
    deadweight_t    INTEGER,
    operator        VARCHAR(128),
    status          VARCHAR(32)  NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT vessels_status_check
        CHECK (status IN ('active', 'inactive', 'maintenance', 'decommissioned')),
    CONSTRAINT vessels_type_check
        CHECK (vessel_type IN ('cargo', 'tanker', 'container', 'bulk',
                               'ro-ro', 'passenger', 'tug', 'fishing', 'other'))
);

CREATE INDEX IF NOT EXISTS ix_vessels_imo    ON vessels (imo);
CREATE INDEX IF NOT EXISTS ix_vessels_mmsi   ON vessels (mmsi);
CREATE INDEX IF NOT EXISTS ix_vessels_name   ON vessels (name);
CREATE INDEX IF NOT EXISTS ix_vessels_status ON vessels (status);

-- ---------- BERTHS ----------------------------------------------------
CREATE TABLE IF NOT EXISTS berths (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code            VARCHAR(32)  NOT NULL UNIQUE,
    name            VARCHAR(128) NOT NULL,
    port_name       VARCHAR(128) NOT NULL DEFAULT 'Baku International Sea Trade Port',
    location        GEOMETRY(POINT, 4326) NOT NULL,
    max_loa_m       NUMERIC(7,2),   -- max length overall
    max_draft_m     NUMERIC(6,2),
    cargo_type      VARCHAR(64),
    status          VARCHAR(32)  NOT NULL DEFAULT 'available',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT berths_status_check
        CHECK (status IN ('available', 'occupied', 'reserved', 'maintenance', 'closed'))
);

CREATE INDEX IF NOT EXISTS ix_berths_status   ON berths (status);
CREATE INDEX IF NOT EXISTS ix_berths_location ON berths USING GIST (location);

-- ---------- PORT BOOKINGS --------------------------------------------
CREATE TABLE IF NOT EXISTS port_bookings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id           UUID NOT NULL REFERENCES vessels(id) ON DELETE CASCADE,
    berth_id            UUID NOT NULL REFERENCES berths(id)  ON DELETE CASCADE,
    eta                 TIMESTAMPTZ NOT NULL,         -- estimated time of arrival
    etd                 TIMESTAMPTZ,                  -- estimated time of departure
    actual_arrival      TIMESTAMPTZ,
    actual_departure    TIMESTAMPTZ,
    status              VARCHAR(32) NOT NULL DEFAULT 'scheduled',
    cargo_description   TEXT,
    booking_reference   VARCHAR(64) UNIQUE,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT port_bookings_status_check
        CHECK (status IN ('scheduled', 'confirmed', 'in_progress',
                          'completed', 'cancelled', 'delayed')),
    CONSTRAINT port_bookings_eta_etd_check
        CHECK (etd IS NULL OR etd >= eta)
);

CREATE INDEX IF NOT EXISTS ix_port_bookings_vessel_id ON port_bookings (vessel_id);
CREATE INDEX IF NOT EXISTS ix_port_bookings_berth_id  ON port_bookings (berth_id);
CREATE INDEX IF NOT EXISTS ix_port_bookings_eta       ON port_bookings (eta);
CREATE INDEX IF NOT EXISTS ix_port_bookings_status    ON port_bookings (status);
-- Hot lookup: bookings for a vessel ordered by ETA
CREATE INDEX IF NOT EXISTS ix_port_bookings_vessel_eta
    ON port_bookings (vessel_id, eta DESC);
-- Hot lookup: berth utilization windows
CREATE INDEX IF NOT EXISTS ix_port_bookings_berth_eta
    ON port_bookings (berth_id, eta);

-- ---------- VESSEL POSITIONS (AIS TELEMETRY) -------------------------
CREATE TABLE IF NOT EXISTS vessel_positions (
    id              BIGSERIAL PRIMARY KEY,
    vessel_id       UUID NOT NULL REFERENCES vessels(id) ON DELETE CASCADE,
    position        GEOMETRY(POINT, 4326) NOT NULL,
    sog_knots       NUMERIC(6,2),     -- speed over ground
    cog_deg         NUMERIC(6,2),     -- course over ground (0-360)
    heading_deg     NUMERIC(6,2),
    nav_status      VARCHAR(48),      -- AIS nav status
    source          VARCHAR(32) NOT NULL DEFAULT 'AIS',
    recorded_at     TIMESTAMPTZ NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT vessel_positions_cog_check
        CHECK (cog_deg     IS NULL OR (cog_deg     >= 0 AND cog_deg     <= 360)),
    CONSTRAINT vessel_positions_heading_check
        CHECK (heading_deg IS NULL OR (heading_deg >= 0 AND heading_deg <= 360))
);

-- Time-series & spatial indexes
CREATE INDEX IF NOT EXISTS ix_vessel_positions_recorded_at
    ON vessel_positions (recorded_at DESC);
CREATE INDEX IF NOT EXISTS ix_vessel_positions_vessel_recorded
    ON vessel_positions (vessel_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS ix_vessel_positions_geom
    ON vessel_positions USING GIST (position);
-- Combined spatio-temporal lookups (e.g. "vessels in this polygon last 24h")
CREATE INDEX IF NOT EXISTS ix_vessel_positions_geom_time
    ON vessel_positions USING GIST (position, recorded_at);

-- ---------- JIT RECOMMENDATIONS --------------------------------------
CREATE TABLE IF NOT EXISTS jit_recommendations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id           UUID NOT NULL REFERENCES vessels(id) ON DELETE CASCADE,
    booking_id          UUID REFERENCES port_bookings(id) ON DELETE CASCADE,
    recommended_speed   NUMERIC(6,2) NOT NULL,        -- knots
    recommended_eta     TIMESTAMPTZ  NOT NULL,
    fuel_savings_t      NUMERIC(10,3),                -- tonnes saved
    co2_savings_kg      NUMERIC(12,2),                -- kg CO2 saved
    confidence          NUMERIC(4,3),                 -- 0.000-1.000
    rationale           TEXT,
    status              VARCHAR(32) NOT NULL DEFAULT 'pending',
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT jit_recommendations_status_check
        CHECK (status IN ('pending', 'accepted', 'rejected', 'expired', 'applied',
                          'OPTIMAL', 'OVERSPEED', 'UNDERSPEED', 'BERTH_READY')),
    CONSTRAINT jit_recommendations_confidence_check
        CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 1))
);

CREATE INDEX IF NOT EXISTS ix_jit_recommendations_vessel_id  ON jit_recommendations (vessel_id);
CREATE INDEX IF NOT EXISTS ix_jit_recommendations_booking_id ON jit_recommendations (booking_id);
CREATE INDEX IF NOT EXISTS ix_jit_recommendations_issued_at  ON jit_recommendations (issued_at DESC);
CREATE INDEX IF NOT EXISTS ix_jit_recommendations_status     ON jit_recommendations (status);

-- ---------- ESG METRICS ----------------------------------------------
CREATE TABLE IF NOT EXISTS esg_metrics (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vessel_id           UUID REFERENCES vessels(id) ON DELETE CASCADE,
    booking_id          UUID REFERENCES port_bookings(id) ON DELETE CASCADE,
    period_start        TIMESTAMPTZ NOT NULL,
    period_end          TIMESTAMPTZ NOT NULL,
    fuel_consumed_t     NUMERIC(12,3),
    co2_emitted_kg      NUMERIC(14,2),
    nox_emitted_kg      NUMERIC(14,2),
    sox_emitted_kg      NUMERIC(14,2),
    waiting_time_hours  NUMERIC(8,2),
    distance_nm         NUMERIC(10,2),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT esg_metrics_period_check
        CHECK (period_end >= period_start)
);

CREATE INDEX IF NOT EXISTS ix_esg_metrics_vessel_id   ON esg_metrics (vessel_id);
CREATE INDEX IF NOT EXISTS ix_esg_metrics_booking_id  ON esg_metrics (booking_id);
CREATE INDEX IF NOT EXISTS ix_esg_metrics_period      ON esg_metrics (period_start, period_end);

-- ---------- updated_at TRIGGER ---------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'users','vessels','berths','port_bookings','jit_recommendations'
    ] LOOP
        EXECUTE format(
            'DROP TRIGGER IF EXISTS trg_%1$s_updated_at ON %1$s;
             CREATE TRIGGER trg_%1$s_updated_at
             BEFORE UPDATE ON %1$s
             FOR EACH ROW EXECUTE FUNCTION set_updated_at();', t);
    END LOOP;
END$$;
