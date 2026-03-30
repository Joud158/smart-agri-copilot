from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    session_id: str
    message: str
    history: list[dict[str, str]]

    route: list[str]
    pending_routes: list[str]
    current_route: str | None
    iteration_count: int

    extracted_crop: str | None
    extracted_region: str | None
    extracted_stage: str | None
    extracted_area_m2: float | None
    extracted_soil_ph: float | None
    extracted_organic_matter_pct: float | None
    extracted_soil_texture: str | None
    extracted_month: str | None

    crop_results: list[dict[str, Any]]
    pest_results: list[dict[str, Any]]
    market_results: list[dict[str, Any]]
    irrigation_result: dict[str, Any] | None
    soil_result: dict[str, Any] | None

    final_sources: list[dict[str, Any]]
    final_answer: str
    debug_trace: list[str]
