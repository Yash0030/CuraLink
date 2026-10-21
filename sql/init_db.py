#!/usr/bin/env python3
"""Database initialization script for Personal Health Record Organizer.

Applies sql/schema.sql to PostgreSQL / Neon database.
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

def init_database(db_url: str = None) -> bool:
    url = db_url or DATABASE_URL
    if not url:
        print("[ERROR] DATABASE_URL is not set. Please set it in backend/.env or pass as argument.")
        return False

    schema_file = Path(__file__).parent / "schema.sql"
    if not schema_file.exists():
        print(f"[ERROR] Schema file not found at {schema_file}")
        return False

    print(f"Connecting to database...")
    try:
        # For pooled connection / Neon, prepare_threshold=None prevents prepared statement issues
        with psycopg.connect(url, prepare_threshold=None) as conn:
            with conn.cursor() as cur:
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
    url_arg = sys.argv[1] if len(sys.argv) > 1 else None
    success = init_database(url_arg)
    sys.exit(0 if success else 1)
