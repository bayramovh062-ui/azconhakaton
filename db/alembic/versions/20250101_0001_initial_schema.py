"""Initial NexusAZ schema (PostGIS, vessels, AIS telemetry, JIT, ESG).

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# Alembic identifiers
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------- Extensions ----------------
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "postgis"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gist"')

    # ---------------- users ----------------
    op.create_table(
        "users",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255)),
        sa.Column("role", sa.String(32), nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "role IN ('admin', 'operator', 'analyst', 'viewer')",
            name="users_role_check",
        ),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ---------------- vessels ----------------
    op.create_table(
        "vessels",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("imo", sa.String(16), nullable=False, unique=True),
        sa.Column("mmsi", sa.String(16), unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("call_sign", sa.String(16)),
        sa.Column("vessel_type", sa.String(64), nullable=False, server_default="cargo"),
        sa.Column("flag", sa.String(64)),
        sa.Column("length_m", sa.Numeric(7, 2)),
        sa.Column("beam_m", sa.Numeric(7, 2)),
        sa.Column("draft_m", sa.Numeric(6, 2)),
        sa.Column("gross_tonnage", sa.Integer),
        sa.Column("deadweight_t", sa.Integer),
        sa.Column("operator", sa.String(128)),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance', 'decommissioned')",
            name="vessels_status_check",
        ),
        sa.CheckConstraint(
            "vessel_type IN ('cargo', 'tanker', 'container', 'bulk', "
            "'ro-ro', 'passenger', 'tug', 'fishing', 'other')",
            name="vessels_type_check",
        ),
    )
    op.create_index("ix_vessels_imo", "vessels", ["imo"])
    op.create_index("ix_vessels_mmsi", "vessels", ["mmsi"])
    op.create_index("ix_vessels_name", "vessels", ["name"])
    op.create_index("ix_vessels_status", "vessels", ["status"])

    # ---------------- berths ----------------
    op.create_table(
        "berths",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("port_name", sa.String(128), nullable=False,
                  server_default="Baku International Sea Trade Port"),
        sa.Column("location",
                  Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("max_loa_m", sa.Numeric(7, 2)),
        sa.Column("max_draft_m", sa.Numeric(6, 2)),
        sa.Column("cargo_type", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False, server_default="available"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('available', 'occupied', 'reserved', 'maintenance', 'closed')",
            name="berths_status_check",
        ),
    )
    op.create_index("ix_berths_status", "berths", ["status"])
    # GeoAlchemy2 auto-creates a GIST index on Geometry; we define an explicit
    # named one to keep parity with schema.sql.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_berths_location "
        "ON berths USING GIST (location)"
    )

    # ---------------- port_bookings ----------------
    op.create_table(
        "port_bookings",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("vessel_id", PG_UUID(as_uuid=True),
                  sa.ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("berth_id", PG_UUID(as_uuid=True),
                  sa.ForeignKey("berths.id", ondelete="CASCADE"), nullable=False),
        sa.Column("eta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("etd", sa.DateTime(timezone=True)),
        sa.Column("actual_arrival", sa.DateTime(timezone=True)),
        sa.Column("actual_departure", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False, server_default="scheduled"),
        sa.Column("cargo_description", sa.Text),
        sa.Column("booking_reference", sa.String(64), unique=True),
        sa.Column("created_by", PG_UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('scheduled', 'confirmed', 'in_progress', "
            "'completed', 'cancelled', 'delayed')",
            name="port_bookings_status_check",
        ),
        sa.CheckConstraint(
            "etd IS NULL OR etd >= eta", name="port_bookings_eta_etd_check"
        ),
    )
    op.create_index("ix_port_bookings_vessel_id", "port_bookings", ["vessel_id"])
    op.create_index("ix_port_bookings_berth_id", "port_bookings", ["berth_id"])
    op.create_index("ix_port_bookings_eta", "port_bookings", ["eta"])
    op.create_index("ix_port_bookings_status", "port_bookings", ["status"])
    op.create_index("ix_port_bookings_vessel_eta",
                    "port_bookings", ["vessel_id", "eta"])
    op.create_index("ix_port_bookings_berth_eta",
                    "port_bookings", ["berth_id", "eta"])

    # ---------------- vessel_positions ----------------
    op.create_table(
        "vessel_positions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("vessel_id", PG_UUID(as_uuid=True),
                  sa.ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("position",
                  Geometry(geometry_type="POINT", srid=4326), nullable=False),
        sa.Column("sog_knots", sa.Numeric(6, 2)),
        sa.Column("cog_deg", sa.Numeric(6, 2)),
        sa.Column("heading_deg", sa.Numeric(6, 2)),
        sa.Column("nav_status", sa.String(48)),
        sa.Column("source", sa.String(32), nullable=False, server_default="AIS"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "cog_deg IS NULL OR (cog_deg >= 0 AND cog_deg <= 360)",
            name="vessel_positions_cog_check",
        ),
        sa.CheckConstraint(
            "heading_deg IS NULL OR (heading_deg >= 0 AND heading_deg <= 360)",
            name="vessel_positions_heading_check",
        ),
    )
    op.create_index("ix_vessel_positions_recorded_at",
                    "vessel_positions", [sa.text("recorded_at DESC")])
    op.create_index("ix_vessel_positions_vessel_recorded",
                    "vessel_positions", ["vessel_id", sa.text("recorded_at DESC")])
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_vessel_positions_geom "
        "ON vessel_positions USING GIST (position)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_vessel_positions_geom_time "
        "ON vessel_positions USING GIST (position, recorded_at)"
    )

    # ---------------- jit_recommendations ----------------
    op.create_table(
        "jit_recommendations",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("vessel_id", PG_UUID(as_uuid=True),
                  sa.ForeignKey("vessels.id", ondelete="CASCADE"), nullable=False),
        sa.Column("booking_id", PG_UUID(as_uuid=True),
                  sa.ForeignKey("port_bookings.id", ondelete="CASCADE")),
        sa.Column("recommended_speed", sa.Numeric(6, 2), nullable=False),
        sa.Column("recommended_eta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fuel_savings_t", sa.Numeric(10, 3)),
        sa.Column("co2_savings_kg", sa.Numeric(12, 2)),
        sa.Column("confidence", sa.Numeric(4, 3)),
        sa.Column("rationale", sa.Text),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'expired', 'applied', "
            "'OPTIMAL', 'OVERSPEED', 'UNDERSPEED', 'BERTH_READY')",
            name="jit_recommendations_status_check",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="jit_recommendations_confidence_check",
        ),
    )
    op.create_index("ix_jit_recommendations_vessel_id",
                    "jit_recommendations", ["vessel_id"])
    op.create_index("ix_jit_recommendations_booking_id",
                    "jit_recommendations", ["booking_id"])
    op.create_index("ix_jit_recommendations_issued_at",
                    "jit_recommendations", [sa.text("issued_at DESC")])
    op.create_index("ix_jit_recommendations_status",
                    "jit_recommendations", ["status"])

    # ---------------- esg_metrics ----------------
    op.create_table(
        "esg_metrics",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("vessel_id", PG_UUID(as_uuid=True),
                  sa.ForeignKey("vessels.id", ondelete="CASCADE")),
        sa.Column("booking_id", PG_UUID(as_uuid=True),
                  sa.ForeignKey("port_bookings.id", ondelete="CASCADE")),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fuel_consumed_t", sa.Numeric(12, 3)),
        sa.Column("co2_emitted_kg", sa.Numeric(14, 2)),
        sa.Column("nox_emitted_kg", sa.Numeric(14, 2)),
        sa.Column("sox_emitted_kg", sa.Numeric(14, 2)),
        sa.Column("waiting_time_hours", sa.Numeric(8, 2)),
        sa.Column("distance_nm", sa.Numeric(10, 2)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(
            "period_end >= period_start", name="esg_metrics_period_check"
        ),
    )
    op.create_index("ix_esg_metrics_vessel_id", "esg_metrics", ["vessel_id"])
    op.create_index("ix_esg_metrics_booking_id", "esg_metrics", ["booking_id"])
    op.create_index("ix_esg_metrics_period",
                    "esg_metrics", ["period_start", "period_end"])

    # ---------------- updated_at trigger ----------------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for tbl in ("users", "vessels", "berths", "port_bookings", "jit_recommendations"):
        op.execute(
            f"CREATE TRIGGER trg_{tbl}_updated_at "
            f"BEFORE UPDATE ON {tbl} "
            f"FOR EACH ROW EXECUTE FUNCTION set_updated_at();"
        )


def downgrade() -> None:
    for tbl in ("jit_recommendations", "port_bookings", "berths",
                "vessels", "users"):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_updated_at ON {tbl};")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at();")

    op.drop_table("esg_metrics")
    op.drop_table("jit_recommendations")
    op.execute("DROP INDEX IF EXISTS ix_vessel_positions_geom_time")
    op.execute("DROP INDEX IF EXISTS ix_vessel_positions_geom")
    op.drop_table("vessel_positions")
    op.drop_table("port_bookings")
    op.execute("DROP INDEX IF EXISTS ix_berths_location")
    op.drop_table("berths")
    op.drop_table("vessels")
    op.drop_table("users")

    # Extensions are intentionally NOT dropped — they may be shared with other
    # databases / schemas. Uncomment if you really want a clean slate:
    # op.execute('DROP EXTENSION IF EXISTS "btree_gist"')
    # op.execute('DROP EXTENSION IF EXISTS "postgis"')
    # op.execute('DROP EXTENSION IF EXISTS "pgcrypto"')
