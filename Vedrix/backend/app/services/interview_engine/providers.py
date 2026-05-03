import logging
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from app.core.config import settings

logger = logging.getLogger(__name__)

def _get_llm_with_fallback(primary_model: str, fallback_model: str, temperature: float = 0.7):
    """
    Creates an LLM chain with a robust fallback and explicit logging.
    If NVIDIA (Primary) fails, it logs the error and switches to OpenRouter (Fallback).
    """
    primary = ChatOpenAI(
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
        model=primary_model,
        temperature=temperature
    )
    
    fallback = ChatOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        model=fallback_model,
        temperature=temperature
    )
    
    # Custom logger wrapper to catch and report NVIDIA failures
    def primary_with_logging(input, config=None):
        try:
            return primary.invoke(input, config=config)
        except Exception as e:
            logger.warning(
                f"CRITICAL: Primary Provider (NVIDIA: {primary_model}) FAILED. "
                f"Error: {str(e)}. Falling back to OpenRouter ({fallback_model})."
            )
            raise e # Raise to trigger the LangChain fallback mechanism

    primary_runnable = RunnableLambda(primary_with_logging)
    
    return primary_runnable.with_fallbacks([fallback])

def get_fast_llm():
    """Reference Task 1: Question Generation. Primary: NVIDIA Llama 3.1 8B. Fallback: OR Llama 3.1 8B Free."""
    return _get_llm_with_fallback(
        primary_model="meta/llama-3.1-8b-instruct",
        fallback_model="meta-llama/llama-3.1-8b-instruct:free",
        temperature=0.7
    )

def get_adaptive_llm():
    """Reference Task 2: Adaptive Follow-ups. Primary: NVIDIA Llama 3.1 70B. Fallback: OR Llama 3.3 70B Free."""
    return _get_llm_with_fallback(
        primary_model="meta/llama-3.1-70b-instruct",
        fallback_model="meta-llama/llama-3.3-70b-instruct:free",
        temperature=0.4
    )

def get_strong_llm():
    """Reference Task 3: Comprehensive Feedback Analysis. Primary: NVIDIA Llama 3.1 405B. Fallback: OR Qwen 72B Free."""
    return _get_llm_with_fallback(
        primary_model="meta/llama-3.1-405b-instruct",
        fallback_model="qwen/qwen-2.5-72b-instruct:free",
        temperature=0.1
    )

def get_code_llm():
    """Reference Task 4: Code Evaluation. Primary: NVIDIA Llama 3.1 405B. Fallback: OR Llama 3.1 405B Free."""
    return _get_llm_with_fallback(
        primary_model="meta/llama-3.1-405b-instruct",
        fallback_model="meta-llama/llama-3.1-405b-instruct:free",
        temperature=0.0
    )

def get_fallback_llm():
    """Production Fallback: Reliable free model from OR."""
    return ChatOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        model="google/gemini-2.0-flash-exp:free",
        temperature=0.7
    )
