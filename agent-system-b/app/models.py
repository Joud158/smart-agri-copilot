from typing import Any

from pydantic import BaseModel, Field


class AgentBRequest(BaseModel):
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentBResponse(BaseModel):
    answer: str
    mode: str
    structured_result: dict[str, Any]
