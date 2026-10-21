#!/usr/bin/env python3
"""Database initialization script for Personal Health Record Organizer.

Applies sql/schema.sql to PostgreSQL / Neon database.
Detects outdated table schemas and supports --reset flag.
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

APP_TABLES = ["approvals", "events", "reports", "candidates", "runs"]

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
                # Check if existing tables are from an outdated schema missing patient_key
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='runs' AND column_name='patient_key'")
                has_patient_key = cur.fetchone() is not None

                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='runs'")
                runs_exists = cur.fetchone() is not None

                should_drop = reset or (runs_exists and not has_patient_key)

                if should_drop:
                    print("Detected outdated or requested reset of application tables. Recreating fresh schema...")
                    for tbl in APP_TABLES:
                        cur.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE;")
                    conn.commit()

                # Read and execute schema
                with open(schema_file, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                cur.execute(schema_sql)

            conn.commit()

        print("[SUCCESS] Schema initialized successfully. All tables and indexes are ready.")
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
