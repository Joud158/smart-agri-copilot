from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.config import Settings


def build_chat_model(settings: Settings) -> ChatOpenAI:
    """Create the chat model used by the synthesis step.

    We keep this factory isolated so the rest of the code does not need to know
    provider details, base URLs, or model names.
    """

    return ChatOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        model=settings.openai_model,
        temperature=0.1,
        timeout=settings.request_timeout_seconds,
    )
