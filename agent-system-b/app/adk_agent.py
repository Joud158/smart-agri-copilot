from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.domain_logic import assess_frost_risk, calculate_irrigation_plan, estimate_spray_window

try:
    from google.adk import Runner
    from google.adk.agents.llm_agent import Agent as ADKAgent
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types

    ADK_AVAILABLE = True
except Exception:  # noqa: BLE001 - safe fallback if package or runtime changes
    ADK_AVAILABLE = False
    Runner = None  # type: ignore
    ADKAgent = None  # type: ignore
    InMemorySessionService = None  # type: ignore
    genai_types = None  # type: ignore


def build_root_agent():
    """Create a Google ADK agent when the library is available."""

    if not ADK_AVAILABLE:
        return None

    settings = get_settings()

    def get_region_weather_profile(region: str) -> dict[str, Any]:
        """Return a lightweight simulated weather profile for a Lebanese region."""
        if region.lower() == "bekaa":
            return {"region": region, "summary": "hot dry inland conditions", "eto_mm_day": 6.2}
        if region.lower() in {"mountain", "mountains"}:
            return {"region": region, "summary": "cooler elevated conditions", "eto_mm_day": 4.2}
        return {"region": region, "summary": "milder coastal-to-general conditions", "eto_mm_day": 5.0}

    def irrigation_tool(crop: str, growth_stage: str, region: str, area_m2: float) -> dict[str, Any]:
        """Calculate an irrigation estimate for the provided crop context."""
        return calculate_irrigation_plan(crop, region, growth_stage, area_m2)

    def frost_tool(region: str, growth_stage: str) -> dict[str, Any]:
        """Assess frost sensitivity in a region."""
        return assess_frost_risk(region, growth_stage)

    def spray_tool(region: str) -> dict[str, Any]:
        """Suggest a spray timing window."""
        return estimate_spray_window(region)

    root_agent = ADKAgent(
        model=settings.adk_model,
        name="weather_irrigation_planner",
        description="Independent weather-aware irrigation planning service for agriculture.",
        instruction=(
            "You are the independent irrigation and weather planning service for a smart agriculture platform. "
            "Use the provided tools whenever crop, stage, region, or area are available. "
            "Keep the answer concise, practical, and grounded in the tool outputs."
        ),
        tools=[get_region_weather_profile, irrigation_tool, frost_tool, spray_tool],
    )
    return root_agent


class ADKRuntime:
    """Programmatic ADK runner used by the FastAPI service."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.root_agent = build_root_agent()
        self.session_service = InMemorySessionService() if ADK_AVAILABLE and self.root_agent is not None else None
        self.runner = (
            Runner(agent=self.root_agent, app_name="smart_agri_agent_b", session_service=self.session_service)
            if ADK_AVAILABLE and self.root_agent is not None
            else None
        )
        self.user_id = self.settings.agent_b_user_id

    async def run_turn(self, query: str, session_id: str) -> str:
        if not ADK_AVAILABLE or self.runner is None or self.session_service is None or genai_types is None:
            raise RuntimeError("google-adk-unavailable")

        existing = await self.session_service.get_session(
            app_name="smart_agri_agent_b",
            user_id=self.user_id,
            session_id=session_id,
        )
        if existing is None:
            await self.session_service.create_session(
                app_name="smart_agri_agent_b",
                user_id=self.user_id,
                session_id=session_id,
            )

        content = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])
        final_response = None
        async for event in self.runner.run_async(user_id=self.user_id, session_id=session_id, new_message=content):
            if event.is_final_response():
                if getattr(event, "content", None) and getattr(event.content, "parts", None):
                    final_response = event.content.parts[0].text
                elif getattr(event, "error_message", None):
                    final_response = f"ADK runtime error: {event.error_message}"
                break
        if not final_response:
            raise RuntimeError("adk-no-final-response")
        return final_response.strip()
