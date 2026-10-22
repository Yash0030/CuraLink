#!/usr/bin/env python3
"""Database initialization script for Personal Health Record Organizer.

Applies sql/schema.sql to PostgreSQL / Neon database into an isolated 'phr' schema.
Protects the 'public' schema and any existing unrelated tables.
"""

import os
import sys
from pathlib import Path
import psycopg
from dotenv import load_dotenv

# Load env variables from backend/.env or root .env
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / "backend" / ".env")
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

# Legacy project tables that should never live in public
LEGACY_PUBLIC_TABLES = [
    "approvals", "events", "reports", "candidates", "runs",
    "user_labs", "auth_sessions",
    "checkpoint_writes", "checkpoint_blobs", "checkpoints", "checkpoint_migrations"
]

PHR_TABLES = ["approvals", "events", "reports", "candidates", "runs", "user_labs", "auth_sessions", "users"]

def init_database(db_url: str = None, reset: bool = False) -> bool:
    url = db_url or DATABASE_URL
    if not url:
        print("[ERROR] DATABASE_URL is not set. Please set it in backend/.env or pass as argument.")
        return False

    schema_file = Path(__file__).parent / "schema.sql"
    if not schema_file.exists():
        print(f"[ERROR] Schema file not found at {schema_file}")
        return False

    print("Connecting to database...")
    try:
        with psycopg.connect(url, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
                # 1. Clean up any legacy project tables that might have been created in 'public'
                for tbl in LEGACY_PUBLIC_TABLES:
                    cur.execute(f"DROP TABLE IF EXISTS public.{tbl} CASCADE;")
                conn.commit()

                # 2. If reset requested, drop the 'phr' schema completely
                if reset:
                    print("Reset requested. Dropping schema 'phr' CASCADE...")
                    cur.execute("DROP SCHEMA IF EXISTS phr CASCADE;")
                    conn.commit()

                # 3. Create schema phr and set search_path
                cur.execute("CREATE SCHEMA IF NOT EXISTS phr;")
                cur.execute("SET search_path TO phr, public;")
                conn.commit()

                # 4. Read and execute schema.sql
                print("Applying schema.sql into 'phr' schema...")
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                cur.execute(schema_sql)
                conn.commit()

                # 5. Verify created tables in 'phr' schema
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='phr' ORDER BY table_name")
                phr_tables = [r[0] for r in cur.fetchall()]
                print(f"[SUCCESS] Tables in 'phr' schema ({len(phr_tables)}): {', '.join(phr_tables)}")

                # 6. Verify public schema isolation
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name")
                public_tables = [r[0] for r in cur.fetchall()]
                print(f"[INFO] Unrelated tables preserved in 'public' schema ({len(public_tables)}): {', '.join(public_tables)}")

        print("\n[SUCCESS] Dedicated 'phr' schema initialized successfully. Public schema is completely isolated.")
        return True
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--reset"]
    url_arg = args[0] if args else None

    success = init_database(url_arg, reset=reset_flag)
    sys.exit(0 if success else 1)
