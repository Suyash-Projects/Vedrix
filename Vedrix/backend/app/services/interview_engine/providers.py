import logging
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_llm_with_fallback(primary_model: str, fallback_model: str, primary_provider: str = "nvidia", fallback_provider: str = "groq", temperature: float = 0.7):
    """
    Creates an LLM chain with a robust fallback and explicit logging.
    Supports NVIDIA + Groq (both working). OpenRouter disabled (expired key).
    """
    def make_llm(provider: str, model: str):
        if provider == "nvidia":
            return ChatOpenAI(
                api_key=settings.NVIDIA_API_KEY,
                base_url=settings.NVIDIA_BASE_URL,
                model=model,
                temperature=temperature,
                max_retries=0
            )
        elif provider == "groq":
            return ChatOpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url=settings.GROQ_BASE_URL,
                model=model,
                temperature=temperature,
                max_retries=0
            )

    primary = make_llm(primary_provider, primary_model)
    fallback = make_llm(fallback_provider, fallback_model)

    # Custom logger wrapper to catch and report provider failures
    async def primary_with_logging(input, config=None):
        try:
            return await primary.ainvoke(input, config=config)
        except Exception as e:
            logger.warning(
                f"CRITICAL: Primary Provider ({primary_provider.upper()}: {primary_model}) FAILED. "
                f"Error: {str(e)}. Falling back to {fallback_provider.upper()} ({fallback_model})."
            )
            raise e  # Raise to trigger the LangChain fallback mechanism

    primary_runnable = RunnableLambda(primary_with_logging)

    return primary_runnable.with_fallbacks([fallback])


def get_fast_llm():
    """Question Generation. Primary: NVIDIA Llama 3.1 8B. Fallback: Groq Llama 3.1 8B Instant."""
    return _get_llm_with_fallback(
        primary_model="meta/llama-3.1-8b-instruct",
        fallback_model="llama-3.1-8b-instant",
        primary_provider="nvidia",
        fallback_provider="groq",
        temperature=0.7
    )


def get_adaptive_llm():
    """Adaptive Follow-ups. Primary: NVIDIA Llama 3.1 70B. Fallback: Groq Llama 3.3 70B."""
    return _get_llm_with_fallback(
        primary_model="meta/llama-3.1-70b-instruct",
        fallback_model="llama-3.3-70b-versatile",
        primary_provider="nvidia",
        fallback_provider="groq",
        temperature=0.4
    )


def get_strong_llm():
    """Comprehensive Feedback Analysis. Primary: NVIDIA 70B. Fallback: Groq 70B."""
    # NOTE: NVIDIA 405B was retired (HTTP 410). Using 70B as primary with Groq 70B fallback.
    return _get_llm_with_fallback(
        primary_model="meta/llama-3.1-70b-instruct",
        fallback_model="llama-3.3-70b-versatile",
        primary_provider="nvidia",
        fallback_provider="groq",
        temperature=0.1
    )


def get_code_llm():
    """Code Evaluation. Primary: Groq 70B. Fallback: Groq 8B (both free tier)."""
    # NOTE: NVIDIA 405B retired. Groq offers reliable free-tier code evaluation.
    return _get_llm_with_fallback(
        primary_model="llama-3.3-70b-versatile",
        fallback_model="llama-3.1-8b-instant",
        primary_provider="groq",
        fallback_provider="groq",
        temperature=0.0
    )


def get_fallback_llm():
    """Production Fallback: Groq Llama 3.1 8B Instant (reliable and fast)."""
    return ChatOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url=settings.GROQ_BASE_URL,
        model="llama-3.1-8b-instant",
        temperature=0.7
    )
