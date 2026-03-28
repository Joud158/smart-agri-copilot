from typing import Any, TypedDict


class GraphState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes.

    Keeping the state explicit makes debugging and explanation much easier.
    """

    session_id: str
    message: str
    history: list[dict[str, str]]
    route: list[str]
    extracted_crop: str | None
    extracted_region: str | None
    extracted_stage: str | None
    crop_results: list[dict[str, Any]]
    pest_results: list[dict[str, Any]]
    market_results: list[dict[str, Any]]
    irrigation_result: dict[str, Any] | None
    soil_result: dict[str, Any] | None
    final_sources: list[dict[str, Any]]
    final_answer: str
    debug_trace: list[str]
