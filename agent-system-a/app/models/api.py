from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Incoming user message.

    `session_id` is optional so the frontend can start a conversation without
    having to create a server-side session beforehand.
    """

    message: str = Field(..., min_length=1, description="User question or instruction.")
    session_id: str | None = Field(default=None, description="Stable conversation ID.")
    stream: bool = Field(default=False, description="Optional convenience flag.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra UI or demo metadata.")


class SourceSnippet(BaseModel):
    """Retrieved evidence returned for transparency and evaluation."""

    source_path: str
    title: str
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Unified API response from Agent System A."""

    session_id: str
    route: list[str]
    answer: str
    disclaimer: str
    sources: list[SourceSnippet] = Field(default_factory=list)
    debug_trace: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
