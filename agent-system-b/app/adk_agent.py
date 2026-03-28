from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.domain_logic import assess_frost_risk, calculate_irrigation_plan, estimate_spray_window

try:
    from google.adk.agents.llm_agent import Agent as ADKAgent
    ADK_AVAILABLE = True
except Exception:  # noqa: BLE001 - safe fallback if package or runtime changes
    ADK_AVAILABLE = False
    ADKAgent = None  # type: ignore


def build_root_agent():
    """Create a Google ADK agent when the library is available.

    The ADK path is kept isolated here so the service can remain framework-distinct
    from Agent System A while still providing a deterministic fallback for local demos.
    """

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
            "You are a specialized agriculture service. Use tools to estimate irrigation, "
            "assess frost risk, and suggest spray timing. Be practical and cautious."
        ),
        tools=[get_region_weather_profile, irrigation_tool, frost_tool, spray_tool],
    )
    return root_agent
