from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.config import Settings
from app.services.mcp_client import MCPToolClient


class ServiceClients:
    """Shared HTTP clients with retry / backoff for transient failures."""

    RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.timeout = httpx.Timeout(settings.request_timeout_seconds)
        self.mcp_client = MCPToolClient(settings)

    async def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        attempts = max(self.settings.service_retry_attempts, 1)

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, json=payload)
                    if response.status_code in self.RETRYABLE_STATUS_CODES:
                        response.raise_for_status()
                    response.raise_for_status()
                    return response.json()
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                status_code = getattr(exc.response, "status_code", None) if isinstance(exc, httpx.HTTPStatusError) else None
                should_retry = attempt < attempts and (status_code in self.RETRYABLE_STATUS_CODES or status_code is None)
                if not should_retry:
                    raise
                await asyncio.sleep((self.settings.service_retry_backoff_ms / 1000.0) * attempt)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Unexpected empty retry loop in ServiceClients._post_json")

    async def call_agent_b(self, message: str, metadata: dict[str, Any], session_id: str | None = None) -> dict[str, Any]:
        payload = {"message": message, "metadata": metadata}
        if session_id:
            payload["session_id"] = session_id
        return await self._post_json(f"{self.settings.agent_b_url}/chat", payload)

    async def call_mcp_tool(self, tool_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.settings.enable_mcp_client:
            try:
                return await self.mcp_client.call_tool(f"mcp_{tool_name}", payload)
            except Exception:  # noqa: BLE001
                # Fall back to the REST bridge so the app stays available even if the
                # MCP SDK or session bootstrap fails in the runtime environment.
                pass
        return await self._post_json(f"{self.settings.mcp_server_url}/bridge/{tool_name}", payload)
