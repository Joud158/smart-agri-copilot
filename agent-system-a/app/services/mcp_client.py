from __future__ import annotations

from typing import Any

from app.config import Settings

try:
    from mcp import ClientSession
    from mcp.client.streamable_http import streamable_http_client
    MCP_CLIENT_AVAILABLE = True
except Exception:  # noqa: BLE001
    ClientSession = None  # type: ignore
    streamable_http_client = None  # type: ignore
    MCP_CLIENT_AVAILABLE = False


class MCPToolClient:
    """Thin MCP client wrapper used by Agent System A.

    The primary path talks to the MCP server over the canonical Streamable HTTP
    transport. A REST bridge remains available elsewhere as a fallback so the
    system can still demo cleanly if the MCP SDK is unavailable.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if not MCP_CLIENT_AVAILABLE:
            raise RuntimeError("mcp-sdk-unavailable")

        async with streamable_http_client(self.settings.mcp_streamable_http_url) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.call_tool(tool_name, arguments)

        content_items = getattr(response, "content", []) or []
        if not content_items:
            return {"status": "ok", "tool_name": tool_name, "content": []}

        normalized: list[dict[str, Any]] = []
        text_fragments: list[str] = []
        for item in content_items:
            item_type = getattr(item, "type", type(item).__name__)
            text_value = getattr(item, "text", None)
            normalized.append({"type": item_type, "text": text_value})
            if text_value:
                text_fragments.append(str(text_value))

        if len(text_fragments) == 1:
            import json

            try:
                parsed = json.loads(text_fragments[0])
                if isinstance(parsed, dict):
                    return parsed
            except Exception:  # noqa: BLE001
                pass

        return {
            "status": "ok",
            "tool_name": tool_name,
            "content": normalized,
            "answer": "\n".join(text_fragments).strip(),
        }
