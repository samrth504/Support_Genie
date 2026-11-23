"""LLM access with retry + provider fallback.  Nodes/routes NEVER call a provider SDK directly.

    Groq (gpt-oss-120b by default, primary)  --fails-->  Gemini Flash (backup)

Both are wrapped with LangChain's `with_structured_output` (the model must return JSON matching
a Pydantic schema), `.with_retry()` and `.with_fallbacks()`.
"""
import logging
from functools import lru_cache
from typing import TypeVar

from langchain_core.runnables import Runnable
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(RuntimeError):
    """No provider is configured (missing API keys)."""


def _providers():
    settings = get_settings()
    models = []
    if settings.groq_api_key:
        from langchain_groq import ChatGroq

        models.append(("groq", ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
            max_retries=0,  # retries are handled below, per provider
        )))
    if settings.google_api_key:
        from langchain_google_genai import ChatGoogleGenerativeAI

        models.append(("gemini", ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=settings.llm_temperature,
            timeout=settings.llm_timeout_seconds,
        )))
    if not models:
        raise LLMUnavailableError("Set GROQ_API_KEY and/or GOOGLE_API_KEY in backend/.env")
    return models


@lru_cache(maxsize=8)
def structured_llm(schema: type[T]) -> Runnable:
    """A runnable that takes chat messages and returns an instance of `schema`."""
    chains = []
    for name, model in _providers():
        chain = model.with_structured_output(schema).with_retry(stop_after_attempt=2, wait_exponential_jitter=True)
        chains.append(chain.with_config(run_name=f"{name}-{schema.__name__}"))
    primary, *backups = chains
    logger.info("LLM chain for %s: %d provider(s)", schema.__name__, len(chains))
    return primary.with_fallbacks(backups) if backups else primary
