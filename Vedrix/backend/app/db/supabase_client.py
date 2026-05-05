"""
Supabase client — optional secondary database layer.

When SUPABASE_URL and SUPABASE_KEY are set in the environment, this module
provides a Supabase client that can be used to mirror/sync data to a hosted
Postgres database.  When those env vars are absent (local/SQLite-only mode),
`supabase_client` is None and all callers must guard with an `if` check.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client
    from app.core.config import settings

    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        supabase_client: Optional[Client] = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )
        logger.info("Supabase client initialised — dual-write mode active.")
    else:
        supabase_client = None
        logger.info("Supabase not configured — running in SQLite-only mode.")
except Exception as exc:  # pragma: no cover
    supabase_client = None
    logger.warning("Supabase client init failed (will use SQLite only): %s", exc)
