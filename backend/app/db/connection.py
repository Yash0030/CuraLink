"""Database connection management with Neon Postgres connection pool.

Implements:
- AsyncConnectionPool with prepare_threshold=None for Neon pgbouncer pooled URL.
- Direct URL support for LangGraph AsyncPostgresSaver.
- Safe connection acquisition and transaction management.
- Robust fallback/mock storage for testing environments without a live Neon database.
"""

import os
import json
import logging
from typing import AsyncGenerator, Optional, Dict, Any, List
from contextlib import asynccontextmanager
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.config import settings

logger = logging.getLogger(__name__)

_pool: Optional[AsyncConnectionPool] = None

def get_db_pool() -> Optional[AsyncConnectionPool]:
    global _pool
    if _pool is None and settings.DATABASE_URL:
        logger.info("Initializing Neon Postgres AsyncConnectionPool with prepare_threshold=None")
        try:
            _pool = AsyncConnectionPool(
                conninfo=settings.DATABASE_URL,
                min_size=1,
                max_size=10,
                timeout=30.0,
                kwargs={
                    "prepare_threshold": None,  # Critical Neon PgBouncer rule
                    "row_factory": dict_row
                },
                open=False
            )
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            _pool = None
    return _pool

async def init_pool() -> bool:
    """Opens the connection pool if configured."""
    pool = get_db_pool()
    if pool:
        try:
            await pool.open()
            logger.info("Database connection pool opened successfully.")
            return True
        except Exception as e:
            logger.warning(f"Could not open live Postgres pool: {e}. Falling back to in-memory store for dev/testing.")
            return False
    return False

async def close_pool():
    global _pool
    if _pool:
        try:
            await _pool.close()
            logger.info("Database connection pool closed.")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e}")
        _pool = None

@asynccontextmanager
async def get_db_connection():
    """Yields a database connection from the pool, or None if pool unavailable."""
    pool = get_db_pool()
    if pool and pool.closed is False:
        async with pool.connection() as conn:
            yield conn
    else:
        yield None
