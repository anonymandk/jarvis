"""Factory for configured ARGUS LLM providers."""

from __future__ import annotations

import os
from typing import Any

from config.settings import get_settings
from llm_providers.base import BaseLLM
from llm_providers.gemini import GeminiLLM


def create_llm_provider(
    provider: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> BaseLLM:
    """Create a configured provider or report unsupported providers clearly."""
    settings = get_settings()
    selected_provider = (provider or settings.llm.provider).strip().lower()

    if selected_provider == "gemini":
        key = api_key or settings.llm.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "Gemini API key required. Set ARGUS_LLM_GEMINI_API_KEY "
                "or GEMINI_API_KEY."
            )
        return GeminiLLM(api_key=key, **kwargs)

    if selected_provider == "openai":
        raise NotImplementedError(
            "The OpenAI Realtime provider is not implemented yet."
        )

    if selected_provider == "ollama":
        raise NotImplementedError("The Ollama provider is not implemented yet.")

    raise ValueError(f"Unknown LLM provider: {selected_provider}")


def get_llm_provider_from_settings(**kwargs: Any) -> BaseLLM:
    """Create the provider selected by ARGUS settings."""
    return create_llm_provider(**kwargs)
