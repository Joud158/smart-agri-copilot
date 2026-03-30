from typing import Any

from pydantic import BaseModel, Field


class AgentBRequest(BaseModel):
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    session_id: str | None = None


class AgentBResponse(BaseModel):
    answer: str
    mode: str
    session_id: str | None = None
    structured_result: dict[str, Any] = Field(default_factory=dict)
