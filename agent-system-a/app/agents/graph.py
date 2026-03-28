from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.router import decide_routes, extract_entities
from app.models.state import GraphState
from app.rag.retriever import QdrantRetriever
from app.services.guardrails import apply_output_guardrail
from app.services.http_clients import ServiceClients


def _merge_unique_sources(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for item in group:
            key = (item.get("source_path", ""), item.get("text", "")[:80])
            if key not in seen:
                merged.append(item)
                seen.add(key)
    return merged


class FarmAdvisorGraph:
    """Primary LangGraph workflow.

    The graph is intentionally compact:
    - supervisor decides routes
    - specialist nodes gather evidence
    - synthesizer produces the final grounded answer

    This structure is easier to defend in a presentation than a hidden, opaque agent loop.
    """

    def __init__(self, retriever: QdrantRetriever, clients: ServiceClients) -> None:
        self.retriever = retriever
        self.clients = clients
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(GraphState)

        builder.add_node("supervisor", self.supervisor)
        builder.add_node("crop_specialist", self.crop_specialist)
        builder.add_node("pest_specialist", self.pest_specialist)
        builder.add_node("market_specialist", self.market_specialist)
        builder.add_node("irrigation_bridge", self.irrigation_bridge)
        builder.add_node("soil_bridge", self.soil_bridge)
        builder.add_node("synthesizer", self.synthesizer)

        builder.set_entry_point("supervisor")

        builder.add_edge("supervisor", "crop_specialist")
        builder.add_edge("crop_specialist", "pest_specialist")
        builder.add_edge("pest_specialist", "market_specialist")
        builder.add_edge("market_specialist", "irrigation_bridge")
        builder.add_edge("irrigation_bridge", "soil_bridge")
        builder.add_edge("soil_bridge", "synthesizer")
        builder.add_edge("synthesizer", END)

        return builder.compile()

    def supervisor(self, state: GraphState) -> GraphState:
        crop, region, stage = extract_entities(state["message"])
        route = decide_routes(state["message"])

        debug_trace = list(state.get("debug_trace", []))
        debug_trace.append(f"Supervisor routes: {route}")
        if crop:
            debug_trace.append(f"Extracted crop: {crop}")
        if region:
            debug_trace.append(f"Extracted region: {region}")
        if stage:
            debug_trace.append(f"Extracted stage: {stage}")

        return {
            **state,
            "route": route,
            "extracted_crop": crop,
            "extracted_region": region,
            "extracted_stage": stage,
            "debug_trace": debug_trace,
        }

    def crop_specialist(self, state: GraphState) -> GraphState:
        if "crop" not in state.get("route", []):
            return state

        filter_payload = {
            "topic": "crop guide",
            "crop_name": state.get("extracted_crop"),
        }
        results = self.retriever.search(state["message"], filter_payload)
        debug_trace = list(state.get("debug_trace", []))
        debug_trace.append(f"Crop specialist retrieved {len(results)} snippets")
        return {**state, "crop_results": results, "debug_trace": debug_trace}

    def pest_specialist(self, state: GraphState) -> GraphState:
        if "pest" not in state.get("route", []):
            return state

        filter_payload = {
            "crop_name": state.get("extracted_crop"),
        }
        results = self.retriever.search(state["message"], filter_payload)
        debug_trace = list(state.get("debug_trace", []))
        debug_trace.append(f"Pest specialist retrieved {len(results)} snippets")
        return {**state, "pest_results": results, "debug_trace": debug_trace}

    def market_specialist(self, state: GraphState) -> GraphState:
        if "market" not in state.get("route", []):
            return state

        results = self.retriever.search(
            state["message"],
            {"topic": "seasonal_price_trends"},
        ) or self.retriever.search(state["message"], {"use_case": "market_planning"})
        debug_trace = list(state.get("debug_trace", []))
        debug_trace.append(f"Market specialist retrieved {len(results)} snippets")
        return {**state, "market_results": results, "debug_trace": debug_trace}

    async def irrigation_bridge(self, state: GraphState) -> GraphState:
        if "irrigation" not in state.get("route", []):
            return state

        metadata = {
            "crop": state.get("extracted_crop"),
            "region": state.get("extracted_region"),
            "growth_stage": state.get("extracted_stage"),
        }
        debug_trace = list(state.get("debug_trace", []))

        try:
            result = await self.clients.call_agent_b(state["message"], metadata)
            debug_trace.append("Agent B irrigation service call succeeded")
        except Exception as exc:  # noqa: BLE001 - deliberate demo-safe fallback
            result = {
                "answer": "Agent System B was unavailable, so irrigation-specific calculations could not be completed.",
                "mode": "degraded",
            }
            debug_trace.append(f"Agent B fallback used: {type(exc).__name__}")

        return {**state, "irrigation_result": result, "debug_trace": debug_trace}

    async def soil_bridge(self, state: GraphState) -> GraphState:
        if "soil" not in state.get("route", []):
            return state

        payload = {
            "message": state["message"],
            "crop": state.get("extracted_crop"),
            "region": state.get("extracted_region"),
            "growth_stage": state.get("extracted_stage"),
        }
        debug_trace = list(state.get("debug_trace", []))

        try:
            result = await self.clients.call_mcp_tool("analyze_bundle", payload)
            debug_trace.append("MCP bridge call succeeded")
        except Exception as exc:  # noqa: BLE001
            result = {
                "answer": "The soil and fertilizer tool was unavailable during this request.",
                "status": "degraded",
            }
            debug_trace.append(f"MCP fallback used: {type(exc).__name__}")

        return {**state, "soil_result": result, "debug_trace": debug_trace}

    def synthesizer(self, state: GraphState) -> GraphState:
        """Final composition step.

        We intentionally synthesize in deterministic prose rather than requiring
        an LLM for every answer. That keeps the demo robust and transparent.
        """

        crop_results = state.get("crop_results", [])
        pest_results = state.get("pest_results", [])
        market_results = state.get("market_results", [])
        irrigation_result = state.get("irrigation_result")
        soil_result = state.get("soil_result")

        sections: list[str] = []

        if crop_results:
            sections.append("### Crop guidance")
            sections.append(_summarize_results(crop_results))

        if pest_results:
            sections.append("### Pest / disease reasoning")
            sections.append(_summarize_results(pest_results))

        if market_results:
            sections.append("### Market and harvest timing")
            sections.append(_summarize_results(market_results))

        if irrigation_result:
            sections.append("### Irrigation planner")
            sections.append(irrigation_result.get("answer", "No irrigation result returned."))

        if soil_result:
            sections.append("### Soil and fertilizer support")
            if isinstance(soil_result, dict):
                sections.append(soil_result.get("answer", str(soil_result)))
            else:
                sections.append(str(soil_result))

        if not sections:
            sections.append(
                "I could not find enough grounded agriculture evidence to answer confidently. "
                "Please specify the crop, region, growth stage, and whether the issue is about soil, irrigation, pests, or market timing."
            )

        answer = "\n\n".join(sections)
        answer = apply_output_guardrail(answer)

        final_sources = _merge_unique_sources(crop_results, pest_results, market_results)

        return {
            **state,
            "final_answer": answer,
            "final_sources": final_sources,
        }


def _summarize_results(results: list[dict[str, Any]]) -> str:
    bullets: list[str] = []
    for item in results[:3]:
        text = item.get("text", "").strip().replace("\n", " ")
        compact = " ".join(text.split())
        bullets.append(f"- {compact[:260]}...")
    return "\n".join(bullets)
