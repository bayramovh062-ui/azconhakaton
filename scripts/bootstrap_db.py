"""Bootstrap a userland PostgreSQL + PostGIS instance via `pgserver`.

Starts (or reuses) a Postgres data directory under `<repo>/.pgdata`,
creates the `nexusaz` database, enables required extensions, applies
`db/schema.sql`, loads `db/seed.sql`, and prints the connection URI on
stdout in the form expected by SQLAlchemy + asyncpg.

Run:  python scripts/bootstrap_db.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pgserver
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / ".pgdata"
SCHEMA_SQL = ROOT / "db" / "schema.sql"
SEED_SQL = ROOT / "db" / "seed.sql"
DB_NAME = "nexusaz"


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    print(f"[bootstrap] starting pgserver in {DATA_DIR} ...", flush=True)
    server = pgserver.get_server(str(DATA_DIR), cleanup_mode=None)

    psql_uri = server.get_uri()  # postgresql://.../postgres
    print(f"[bootstrap] postgres up: {psql_uri}", flush=True)

    # Build per-database URIs
    app_uri = psql_uri.rsplit("/", 1)[0] + f"/{DB_NAME}"
    async_uri = app_uri.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(psql_uri)
    conn_kwargs = dict(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username or "postgres",
        password=parsed.password or "",
    )

    # 1) Create database if missing — must run with autocommit
    admin = psycopg2.connect(dbname="postgres", **conn_kwargs)
    admin.autocommit = True
    with admin.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DB_NAME,))
        if cur.fetchone():
            print(f"[bootstrap] database {DB_NAME} already exists", flush=True)
        else:
            print(f"[bootstrap] creating database {DB_NAME} ...", flush=True)
            cur.execute(f'CREATE DATABASE "{DB_NAME}"')
    admin.close()

    # 2) Connect to nexusaz and apply extensions, schema, seed
    app = psycopg2.connect(dbname=DB_NAME, **conn_kwargs)
    app.autocommit = True
    with app.cursor() as cur:
        print("[bootstrap] enabling extensions ...", flush=True)
        cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
        cur.execute('CREATE EXTENSION IF NOT EXISTS "postgis"')
        cur.execute('CREATE EXTENSION IF NOT EXISTS "btree_gist"')

        print(f"[bootstrap] applying {SCHEMA_SQL.name} ...", flush=True)
        cur.execute(SCHEMA_SQL.read_text(encoding="utf-8"))

        print(f"[bootstrap] applying {SEED_SQL.name} ...", flush=True)
        try:
            cur.execute(SEED_SQL.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[bootstrap] seed partial (likely already loaded): {exc}", flush=True)
    app.close()

    # Persist URI for the app
    env_file = ROOT / "backend" / ".env"
    env_file.parent.mkdir(exist_ok=True)
    lines = []
    if env_file.exists():
        for ln in env_file.read_text(encoding="utf-8").splitlines():
            if not ln.startswith("DATABASE_URL=") and not ln.startswith("NEXUSAZ_DATABASE_URL="):
                lines.append(ln)
    lines.insert(0, f"DATABASE_URL={async_uri}")
    lines.insert(1, f"NEXUSAZ_DATABASE_URL={async_uri}")
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[bootstrap] wrote {env_file}", flush=True)

    # Also stamp Alembic so future migrations work cleanly (we used schema.sql)
    print("[bootstrap] stamping alembic head ...", flush=True)
    os.environ["NEXUSAZ_DATABASE_URL"] = async_uri
    os.environ["DATABASE_URL"] = async_uri
    try:
        from alembic import command
        from alembic.config import Config

        cfg = Config(str(ROOT / "db" / "alembic.ini"))
        cfg.set_main_option("script_location", str(ROOT / "db" / "alembic"))
        cfg.set_main_option("sqlalchemy.url", async_uri)
        command.stamp(cfg, "head")
    except Exception as exc:
        print(f"[bootstrap] alembic stamp skipped: {exc}", flush=True)

    print("\n[bootstrap] DONE")
    print(f"[bootstrap] sync URI : {app_uri}")
    print(f"[bootstrap] async URI: {async_uri}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
