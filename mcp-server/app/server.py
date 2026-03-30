from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.routing import Mount

from app.domain_tools import analyze_bundle, analyze_soil, calculate_fertilizer, estimate_water_usage

# -------------------------
# Canonical MCP definition.
# -------------------------
mcp = FastMCP(
    "Smart Agriculture MCP",
    json_response=True,
    streamable_http_path="/",
)


@mcp.tool()
def mcp_analyze_soil(soil_ph: float, organic_matter_pct: float | None = None, texture: str = "loam") -> dict:
    """Interpret a simplified soil profile."""
    return analyze_soil(soil_ph=soil_ph, organic_matter_pct=organic_matter_pct, texture=texture)


@mcp.tool()
def mcp_calculate_fertilizer(crop: str, area_m2: float, soil_type: str = "loam") -> dict:
    """Return a high-level fertilizer direction and rough quantity estimate."""
    return calculate_fertilizer(crop=crop, area_m2=area_m2, soil_type=soil_type)


@mcp.tool()
def mcp_estimate_water_usage(crop: str, area_m2: float, month: str = "july") -> dict:
    """Estimate daily water requirement in liters for a given crop and area."""
    return estimate_water_usage(crop=crop, area_m2=area_m2, month=month)


# -------------------------
# REST bridge.
# -------------------------
bridge_api = FastAPI(
    title="Smart Agriculture MCP Bridge",
    version="1.0.0",
    default_response_class=ORJSONResponse,
)


@bridge_api.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "mcp-server"}




@mcp.tool()
def mcp_analyze_bundle(
    message: str,
    crop: str | None = None,
    region: str | None = None,
    growth_stage: str | None = None,
    area_m2: float | None = None,
    soil_ph: float | None = None,
    organic_matter_pct: float | None = None,
    soil_texture: str | None = None,
    month: str | None = None,
) -> dict:
    """Analyze a combined soil / fertilizer / water-planning request."""
    return analyze_bundle(
        message=message,
        crop=crop,
        region=region,
        growth_stage=growth_stage,
        area_m2=area_m2,
        soil_ph=soil_ph,
        organic_matter_pct=organic_matter_pct,
        soil_texture=soil_texture,
        month=month,
    )


@bridge_api.post("/bridge/analyze_soil")
async def bridge_analyze_soil(payload: dict) -> dict:
    return analyze_soil(
        soil_ph=float(payload.get("soil_ph", 6.8)),
        organic_matter_pct=payload.get("organic_matter_pct"),
        texture=str(payload.get("texture", "loam")),
    )


@bridge_api.post("/bridge/calculate_fertilizer")
async def bridge_calculate_fertilizer(payload: dict) -> dict:
    return calculate_fertilizer(
        crop=str(payload.get("crop", "general crop")),
        area_m2=float(payload.get("area_m2", 500)),
        soil_type=str(payload.get("soil_type", "loam")),
    )


@bridge_api.post("/bridge/estimate_water_usage")
async def bridge_estimate_water_usage(payload: dict) -> dict:
    return estimate_water_usage(
        crop=str(payload.get("crop", "general crop")),
        area_m2=float(payload.get("area_m2", 500)),
        month=str(payload.get("month", "july")),
    )


@bridge_api.post("/bridge/analyze_bundle")
async def bridge_analyze_bundle(payload: dict) -> dict:
    return analyze_bundle(
        message=str(payload.get("message", "")),
        crop=payload.get("crop"),
        region=payload.get("region"),
        growth_stage=payload.get("growth_stage"),
        area_m2=payload.get("area_m2"),
        soil_ph=payload.get("soil_ph"),
        organic_matter_pct=payload.get("organic_matter_pct"),
        soil_texture=payload.get("soil_texture"),
        month=payload.get("month"),
    )


@asynccontextmanager
async def lifespan(app: Starlette):
    # We manage the MCP session lifecycle here so the mounted Streamable HTTP app
    # behaves correctly inside the shared ASGI process.
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Mount("/mcp", app=mcp.streamable_http_app()),
        Mount("/", app=bridge_api),
    ],
    lifespan=lifespan,
)
