from __future__ import annotations

from typing import Any

from app.config import Settings


def build_chat_model(settings: Settings) -> Any | None:
    """Create the optional chat model backend.

    The stable submission version defaults to `LLM_PROVIDER=none`, so this
    helper is intentionally lazy and only imports provider packages when a
    provider is actually requested.
    """

    provider = settings.llm_provider.lower().strip()

    if provider == "none":
        return None

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )

    if provider == "openai":
        if not settings.openai_api_key or settings.openai_api_key == "replace_me":
            raise RuntimeError("OPENAI_API_KEY is missing for LLM_PROVIDER=openai")

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
            temperature=0.1,
            timeout=settings.request_timeout_seconds,
        )

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")
