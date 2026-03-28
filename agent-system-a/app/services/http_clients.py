from __future__ import annotations

from typing import Any

import httpx

from app.config import Settings


class ServiceClients:
    """Shared HTTP clients for cross-service calls.

    Why a wrapper class?
    - centralizes timeouts
    - keeps URLs in one place
    - makes fallback behavior easier to reason about
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.timeout = httpx.Timeout(settings.request_timeout_seconds)

    async def call_agent_b(self, message: str, metadata: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.settings.agent_b_url}/chat",
                json={"message": message, "metadata": metadata},
            )
            response.raise_for_status()
            return response.json()

    async def call_mcp_tool(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.settings.mcp_server_url}/bridge/{tool_name}",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
