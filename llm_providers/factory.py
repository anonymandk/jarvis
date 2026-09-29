"""LLM Provider factory for JARVIS.

Creates the appropriate BaseLLM implementation based on configuration.
"""

from __future__ import annotations

from typing import Optional

from config.settings import get_settings
from llm_providers.base import BaseLLM
from llm_providers.gemini import GeminiLLM
from llm_providers.openai import OpenAILLM
from llm_providers.ollama import OllamaLLM


def create_llm_provider(
    provider: str = None,
    api_key: str = None,
    **kwargs,
) -> BaseLLM:
    """Create LLM provider instance.

    Args:
        provider: One of "gemini", "openai", "ollama" (uses settings if None)
        api_key: API key for the provider (uses settings if None)
        **kwargs: Additional arguments passed to provider constructor

    Returns:
        BaseLLM implementation

    Raises:
        ValueError: If provider is unknown or not yet implemented
        NotImplementedError: If provider is a stub (openai, ollama)
    """
    settings = get_settings()

    # Use settings if not explicitly provided
    if provider is None:
        provider = settings.llm.provider

    provider = provider.lower()

    if provider == "gemini":
        key = api_key or settings.llm.gemini_api_key
        if not key:
            raise ValueError(
                "Gemini API key required. Set JARVIS_LLM_GEMINI_API_KEY "
                "or GEMINI_API_KEY environment variable."
            )
        return GeminiLLM(api_key=key, **kwargs)

    elif provider == "openai":
        key = api_key or settings.llm.openai_api_key
        if not key:
            raise ValueError(
                "OpenAI API key required. Set JARVIS_LLM_OPENAI_API_KEY "
                "environment variable."
            )
        return OpenAILLM(api_key=key, **kwargs)

    elif provider == "ollama":
        host = kwargs.pop("host", settings.llm.ollama_host or "http://localhost:11434")
        model = kwargs.pop("model", settings.llm.ollama_model)
        return OllamaLLM(host=host, model=model, **kwargs)

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


def get_llm_provider_from_settings(**kwargs) -> BaseLLM:
    """Create LLM provider from JARVIS settings.

    Reads JARVIS_LLM_PROVIDER env var (via settings) to determine provider.
    """
    return create_llm_provider(**kwargs)