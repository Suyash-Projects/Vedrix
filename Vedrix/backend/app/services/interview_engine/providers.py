"""
LLM Provider Configuration — DEPRECATED.

This module now re-exports from model_router.py for backward compatibility.
New code should import directly from model_router.py:

    from app.services.interview_engine.model_router import (
        get_llm, TaskType, get_fast_llm, get_strong_llm,
        get_code_llm, get_adaptive_llm, get_report_llm,
    )
"""
import logging

from app.services.interview_engine.model_router import (
    get_fast_llm,
    get_adaptive_llm,
    get_strong_llm,
    get_code_llm,
    get_fallback_llm,
    get_llm,
    get_provider_statuses,
    get_route_statuses,
    is_provider_configured,
    TaskType,
    clear_llm_cache,
)

logger = logging.getLogger(__name__)

logger.warning(
    "providers.py is deprecated. Import from model_router.py instead. "
    "Backward compatibility maintained."
)
