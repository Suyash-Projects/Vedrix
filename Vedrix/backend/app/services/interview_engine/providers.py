from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from app.core.config import settings

def get_fast_llm():
    """Returns Groq LLM for fast real-time interaction."""
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model_name="llama-3.1-8b-instant",
        temperature=0.7
    )

def get_strong_llm():
    """Returns NVIDIA LLM (via OpenAI compatible API) for deep analysis."""
    return ChatOpenAI(
        api_key=settings.NVIDIA_API_KEY,
        base_url=settings.NVIDIA_BASE_URL,
        model_name="meta/llama-3.1-405b-instruct",
        temperature=0.1
    )

def get_fallback_llm():
    """Returns OpenRouter/APIFree LLM for fallback."""
    return ChatOpenAI(
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        model_name="openrouter/auto-free",
        temperature=0.7
    )
