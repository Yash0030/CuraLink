"""Checkpointer setup for LangGraph.

Uses AsyncPostgresSaver with Neon direct URL (with -pooler stripped)
managed via AsyncConnectionPool, or MemorySaver when CHECKPOINTER=memory or fallback.
"""

import logging
from typing import Optional, Any
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings

logger = logging.getLogger(__name__)

_memory_saver = MemorySaver()
_postgres_saver: Optional[Any] = None
_postgres_pool: Optional[Any] = None

async def get_checkpointer() -> Any:
    """Returns the configured checkpointer (AsyncPostgresSaver or MemorySaver)."""
    global _postgres_saver, _postgres_pool

    if settings.CHECKPOINTER == "memory" or not settings.direct_checkpoint_url:
        logger.info("Using LangGraph in-memory checkpointer (MemorySaver).")
        return _memory_saver

    if _postgres_saver is not None:
        return _postgres_saver

    try:
        from psycopg_pool import AsyncConnectionPool
        from psycopg.rows import dict_row
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        direct_url = settings.direct_checkpoint_url
        logger.info(f"Setting up AsyncPostgresSaver with connection pool (direct URL: {direct_url.split('@')[-1] if '@' in direct_url else 'configured'})")

        _postgres_pool = AsyncConnectionPool(
            conninfo=direct_url,
            min_size=1,
            max_size=5,
            open=False,
            check=AsyncConnectionPool.check_connection,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            }
        )
        await _postgres_pool.open()

        saver = AsyncPostgresSaver(conn=_postgres_pool)
        # Disable pipeline mode: Neon's proxies / serverless architectures can drop pipelined connections
        saver.supports_pipeline = False

        await saver.setup()
        _postgres_saver = saver
        logger.info("AsyncPostgresSaver successfully initialized with active connection pool.")
        return _postgres_saver
    except Exception as e:
        logger.warning(f"Could not connect AsyncPostgresSaver ({e}). Falling back to MemorySaver.", exc_info=True)
        return _memory_saver

async def close_checkpointer():
    """Closes the checkpointer connection pool on application shutdown."""
    global _postgres_pool, _postgres_saver
    if _postgres_pool is not None:
        try:
            await _postgres_pool.close()
            logger.info("AsyncPostgresSaver connection pool closed.")
        except Exception as e:
            logger.warning(f"Error closing checkpointer pool: {e}")
        _postgres_pool = None
        _postgres_saver = None
