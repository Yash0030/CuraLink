"""Checkpointer setup for LangGraph.

Uses AsyncPostgresSaver with Neon direct URL (with -pooler stripped),
or MemorySaver when CHECKPOINTER=memory or during testing.
"""

import logging
from typing import Optional, Any
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings

logger = logging.getLogger(__name__)

_memory_saver = MemorySaver()
_postgres_saver: Optional[Any] = None

async def get_checkpointer() -> Any:
    """Returns the configured checkpointer (AsyncPostgresSaver or MemorySaver)."""
    global _postgres_saver

    if settings.CHECKPOINTER == "memory" or not settings.direct_checkpoint_url:
        logger.info("Using LangGraph in-memory checkpointer (MemorySaver).")
        return _memory_saver

    if _postgres_saver is not None:
        return _postgres_saver

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        direct_url = settings.direct_checkpoint_url
        logger.info(f"Setting up AsyncPostgresSaver with direct URL: {direct_url.split('@')[-1] if '@' in direct_url else 'configured'}")

        # In langgraph-checkpoint-postgres, from_conn_string is an async context manager
        cm = AsyncPostgresSaver.from_conn_string(direct_url)
        saver = await cm.__aenter__()
        await saver.setup()
        _postgres_saver = saver
        logger.info("AsyncPostgresSaver successfully initialized and tables verified.")
        return _postgres_saver
    except Exception as e:
        logger.warning(f"Could not connect AsyncPostgresSaver ({e}). Falling back to MemorySaver.")
        return _memory_saver
