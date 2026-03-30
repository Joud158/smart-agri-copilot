from __future__ import annotations

from typing import Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph

from app.agents.router import decide_routes, extract_entities
from app.config import Settings
from app.models.state import GraphState
from app.rag.retriever import QdrantRetriever
from app.services.guardrails import apply_output_guardrail
from app.services.http_clients import ServiceClients
from app.services.web_search import WebSearchService

ROUTE_TO_NODE = {
    "crop": "crop_specialist",
    "pest": "pest_specialist",
    "market": "market_specialist",
    "irrigation": "irrigation_bridge",
    "soil": "soil_bridge",
}


def _merge_unique_sources(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    merged: list[dict[str, Any]] = []
    for group in groups:
        for item in group:
            key = (
                item.get("source_path", ""),
                item.get("title", ""),
                item.get("text", "")[:120],
            )
            if key not in seen:
                merged.append(item)
                seen.add(key)
    return merged


class FarmAdvisorGraph:
    """Primary workflow with deterministic routing plus optional ReAct-style tool use.

    ReAct is attempted only when an LLM backend is available. If the model backend
    is missing, rate-limited, or otherwise fails, the workflow falls back to the
    deterministic routed graph instead of crashing the API.
    """

    def __init__(
        self,
        retriever: QdrantRetriever,
        clients: ServiceClients,
        settings: Settings,
        chat_model: Any | None = None,
    ) -> None:
        self.retriever = retriever
        self.clients = clients
        self.settings = settings
        self.chat_model = chat_model
        self.web_search = WebSearchService(enabled=settings.enable_web_search)
        self.graph = self._build_graph()
        self.react_tools = self._build_react_tools() if self.chat_model is not None else {}

    async def answer(self, state: GraphState) -> GraphState:
        if self.chat_model is not None and self.settings.enable_react_agent and self.settings.agent_pattern.lower() == "react":
            try:
                return await self._react_answer(state)
            except Exception as exc:  # noqa: BLE001
                debug_trace = list(state.get("debug_trace", []))
                debug_trace.append(f"ReAct unavailable, falling back to deterministic graph: {type(exc).__name__}")
                fallback_state = {**state, "debug_trace": debug_trace}
                return await self.graph.ainvoke(fallback_state)
        return await self.graph.ainvoke(state)

    def _build_graph(self):
        builder = StateGraph(GraphState)
        builder.add_node("supervisor", self.supervisor)
        builder.add_node("route_dispatcher", self.route_dispatcher)
        builder.add_node("crop_specialist", self.crop_specialist)
        builder.add_node("pest_specialist", self.pest_specialist)
        builder.add_node("market_specialist", self.market_specialist)
        builder.add_node("irrigation_bridge", self.irrigation_bridge)
        builder.add_node("soil_bridge", self.soil_bridge)
        builder.add_node("synthesizer", self.synthesizer)
        builder.set_entry_point("supervisor")
        builder.add_edge("supervisor", "route_dispatcher")
        builder.add_conditional_edges(
            "route_dispatcher",
            self.route_from_dispatcher,
            {
                "crop_specialist": "crop_specialist",
                "pest_specialist": "pest_specialist",
                "market_specialist": "market_specialist",
                "irrigation_bridge": "irrigation_bridge",
                "soil_bridge": "soil_bridge",
                "synthesizer": "synthesizer",
            },
        )
        for node_name in ("crop_specialist", "pest_specialist", "market_specialist", "irrigation_bridge", "soil_bridge"):
            builder.add_edge(node_name, "route_dispatcher")
        builder.add_edge("synthesizer", END)
        return builder.compile()

    def _build_react_tools(self) -> dict[str, Any]:
        @tool
        def rag_search(query: str) -> str:
            """Search indexed agriculture documents and internal knowledge base. Use first for agriculture/domain questions."""
            results = self.retriever.search(query)
            if not results:
                return "No internal RAG results found."
            top = []
            for item in results[: self.settings.top_k]:
                meta = item.get("metadata", {})
                source = item.get("source_path", "unknown")
                top.append(f"[{source}] {item.get('title','Untitled')} :: {item.get('text','')[:350]} :: meta={meta}")
            return "\n\n".join(top)

        @tool
        def web_search_tool(query: str) -> str:
            """Search the public web for current public information when internal docs are insufficient or the user asks for external/current information."""
            results = self.web_search.search(query)
            if not results:
                return "No web results available."
            return "\n\n".join(f"[{r['source_path']}] {r['title']} :: {r['text']}" for r in results[:4])

        return {"rag_search": rag_search, "web_search_tool": web_search_tool}

    async def _react_answer(self, state: GraphState) -> GraphState:
        debug_trace = list(state.get("debug_trace", []))
        llm = self.chat_model.bind_tools(list(self.react_tools.values()))
        messages: list[Any] = [
            SystemMessage(
                content=(
                    "You are a multilingual smart agriculture assistant using the ReAct pattern. "
                    "Prefer rag_search for agriculture knowledge from indexed text documents. "
                    "Use web_search_tool only when the internal documents are insufficient or the question clearly needs current/public information. "
                    "Answer in the user's language when possible. Cite sources inline using source names when available. "
                    "If neither tool gives enough evidence, clearly say what is uncertain."
                )
            ),
            HumanMessage(content=state["message"]),
        ]
        final_sources: list[dict[str, Any]] = []
        route = ["react"]
        for step in range(self.settings.max_tool_steps):
            ai_msg = await llm.ainvoke(messages)
            messages.append(ai_msg)
            debug_trace.append(f"ReAct step {step+1}: tool_calls={len(getattr(ai_msg, 'tool_calls', []) or [])}")
            if not getattr(ai_msg, "tool_calls", None):
                answer = apply_output_guardrail(getattr(ai_msg, "content", "I could not produce an answer."))
                return {**state, "route": route, "final_answer": answer, "final_sources": final_sources, "debug_trace": debug_trace}
            for tc in ai_msg.tool_calls:
                tool_name = tc["name"]
                args = tc.get("args", {})
                route.append(tool_name)
                if tool_name == "rag_search":
                    query = args.get("query", state["message"])
                    results = self.retriever.search(query)
                    final_sources = _merge_unique_sources(final_sources, results)
                    content = self.react_tools[tool_name].invoke(args)
                elif tool_name == "web_search_tool":
                    query = args.get("query", state["message"])
                    results = self.web_search.search(query)
                    final_sources = _merge_unique_sources(final_sources, results)
                    content = self.react_tools[tool_name].invoke(args)
                else:
                    content = f"Unknown tool {tool_name}"
                messages.append(ToolMessage(content=str(content), tool_call_id=tc["id"]))
        answer = apply_output_guardrail("I reached the maximum reasoning steps before completing the request.")
        return {**state, "route": route, "final_answer": answer, "final_sources": final_sources, "debug_trace": debug_trace}

    def supervisor(self, state: GraphState) -> GraphState:
        history = state.get("history", [])
        parsed = extract_entities(state["message"], history)
        route = decide_routes(state["message"], history)
        debug_trace = list(state.get("debug_trace", []))
        debug_trace.append(f"Supervisor routes: {route}")
        return {
            **state,
            "route": route,
            "pending_routes": list(route),
            "current_route": None,
            "iteration_count": 0,
            "extracted_crop": parsed.crop,
            "extracted_region": parsed.region,
            "extracted_stage": parsed.growth_stage,
            "extracted_area_m2": parsed.area_m2,
            "extracted_soil_ph": parsed.soil_ph,
            "extracted_organic_matter_pct": parsed.organic_matter_pct,
            "extracted_soil_texture": parsed.soil_texture,
            "extracted_month": parsed.month,
            "debug_trace": debug_trace,
        }

    def route_dispatcher(self, state: GraphState) -> GraphState:
        pending = list(state.get("pending_routes", []))
        debug_trace = list(state.get("debug_trace", []))
        steps_taken = int(state.get("iteration_count", 0))
        if steps_taken >= self.settings.max_specialist_steps or not pending:
            debug_trace.append("Moving to synthesis")
            return {**state, "current_route": None, "pending_routes": [], "debug_trace": debug_trace}
        current_route = pending.pop(0)
        debug_trace.append(f"Dispatching specialist for route: {current_route}")
        return {**state, "current_route": current_route, "pending_routes": pending, "iteration_count": steps_taken + 1, "debug_trace": debug_trace}

    def route_from_dispatcher(self, state: GraphState) -> Literal["crop_specialist", "pest_specialist", "market_specialist", "irrigation_bridge", "soil_bridge", "synthesizer"]:
        return ROUTE_TO_NODE.get(state.get("current_route"), "synthesizer")

    def _search_with_fallback(self, query: str, primary_filter: dict[str, Any] | None, fallback_filters: list[dict[str, Any] | None] | None = None) -> list[dict[str, Any]]:
        for candidate_filter in [primary_filter] + list(fallback_filters or []):
            results = self.retriever.search(query, candidate_filter)
            if results:
                return results
        return []

    def crop_specialist(self, state: GraphState) -> GraphState:
        results = self._search_with_fallback(state["message"], {"topic": ["crop guide"], "crop_name": state.get("extracted_crop")}, fallback_filters=[{"crop_name": state.get("extracted_crop")}, {"topic": ["crop guide"]}, None])
        debug_trace = list(state.get("debug_trace", []))
        debug_trace.append(f"Crop specialist retrieved {len(results)} snippets")
        return {**state, "crop_results": results, "debug_trace": debug_trace}

    def pest_specialist(self, state: GraphState) -> GraphState:
        results = self._search_with_fallback(state["message"], {"crop_name": state.get("extracted_crop"), "topic": ["pest_disease_index", "greenhouse_ipm", "general_ipm", "symptom_index"]}, fallback_filters=[{"crop_name": state.get("extracted_crop")}, {"topic": ["symptom_index", "greenhouse_ipm", "general_ipm"]}, None])
        debug_trace = list(state.get("debug_trace", []))
        debug_trace.append(f"Pest specialist retrieved {len(results)} snippets")
        return {**state, "pest_results": results, "debug_trace": debug_trace}

    def market_specialist(self, state: GraphState) -> GraphState:
        results = self._search_with_fallback(state["message"], {"topic": ["seasonal_price_trends", "harvest_or_hold_rules"]}, fallback_filters=[{"use_case": "market_planning"}, {"topic": ["harvest_or_hold_rules"]}, None])
        debug_trace = list(state.get("debug_trace", []))
        debug_trace.append(f"Market specialist retrieved {len(results)} snippets")
        return {**state, "market_results": results, "debug_trace": debug_trace}

    async def irrigation_bridge(self, state: GraphState) -> GraphState:
        metadata = {"crop": state.get("extracted_crop"), "region": state.get("extracted_region"), "growth_stage": state.get("extracted_stage"), "area_m2": state.get("extracted_area_m2"), "month": state.get("extracted_month")}
        debug_trace = list(state.get("debug_trace", []))
        try:
            result = await self.clients.call_agent_b(state["message"], metadata, session_id=state.get("session_id"))
            debug_trace.append(f"Agent B irrigation service call succeeded (mode={result.get('mode', 'unknown')})")
        except Exception as exc:  # noqa: BLE001
            result = {"answer": "Agent System B was unavailable, so irrigation-specific calculations could not be completed.", "mode": "degraded", "structured_result": {"error": type(exc).__name__}}
            debug_trace.append(f"Agent B fallback used: {type(exc).__name__}")
        return {**state, "irrigation_result": result, "debug_trace": debug_trace}

    async def soil_bridge(self, state: GraphState) -> GraphState:
        payload = {"message": state["message"], "crop": state.get("extracted_crop"), "region": state.get("extracted_region"), "growth_stage": state.get("extracted_stage"), "area_m2": state.get("extracted_area_m2"), "soil_ph": state.get("extracted_soil_ph"), "organic_matter_pct": state.get("extracted_organic_matter_pct"), "soil_texture": state.get("extracted_soil_texture"), "month": state.get("extracted_month")}
        debug_trace = list(state.get("debug_trace", []))
        try:
            result = await self.clients.call_mcp_tool("analyze_bundle", payload)
            debug_trace.append("MCP bridge call succeeded")
        except Exception as exc:  # noqa: BLE001
            result = {"answer": "The soil and fertilizer tool was unavailable during this request.", "status": "degraded", "structured_result": {"error": type(exc).__name__}}
            debug_trace.append(f"MCP fallback used: {type(exc).__name__}")
        return {**state, "soil_result": result, "debug_trace": debug_trace}

    def synthesizer(self, state: GraphState) -> GraphState:
        crop_results = state.get("crop_results", [])
        pest_results = state.get("pest_results", [])
        market_results = state.get("market_results", [])
        irrigation_result = state.get("irrigation_result")
        soil_result = state.get("soil_result")
        debug_trace = list(state.get("debug_trace", []))
        sections = self._build_deterministic_sections(crop_results, pest_results, market_results, irrigation_result, soil_result)
        internal_sources = _merge_unique_sources(crop_results, pest_results, market_results)
        if self.retriever.should_use_external_fallback(internal_sources) and self.settings.enable_web_search:
            web_results = self.web_search.search(state["message"])
            if web_results:
                sections.append("### Web search fallback")
                sections.append(_summarize_results(web_results))
                internal_sources = _merge_unique_sources(internal_sources, web_results)
                debug_trace.append(f"Web fallback used with {len(web_results)} results")
        answer = "\n\n".join(sections)
        if self.chat_model is not None and internal_sources:
            llm_answer = self._llm_synthesize(state, sections)
            if llm_answer:
                answer = llm_answer
                debug_trace.append("LLM synthesis enabled for final answer")
        answer = apply_output_guardrail(answer)
        return {**state, "final_answer": answer, "final_sources": internal_sources, "debug_trace": debug_trace}

    def _llm_synthesize(self, state: GraphState, sections: list[str]) -> str | None:
        if self.chat_model is None:
            return None
        try:
            messages = [
                SystemMessage(content="You are a practical multilingual agriculture assistant. Use ONLY the provided grounded context. If the context is insufficient, explicitly say so and distinguish internal docs from web fallback. Answer in the user's language whenever reasonable."),
                HumanMessage(content=f"User question: {state['message']}\n\nContext:\n{chr(10).join(sections)}"),
            ]
            response = self.chat_model.invoke(messages)
            content = getattr(response, "content", None)
            if isinstance(content, str) and content.strip():
                return content.strip()
        except Exception:
            return None
        return None

    def _build_deterministic_sections(self, crop_results, pest_results, market_results, irrigation_result, soil_result) -> list[str]:
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
            sections.append(soil_result.get("answer", str(soil_result)) if isinstance(soil_result, dict) else str(soil_result))
        if not sections:
            sections.append("I could not find enough grounded agriculture evidence to answer confidently. Please specify the crop, region, growth stage, and whether the issue is about soil, irrigation, pests, or market timing.")
        return sections


def _summarize_results(results: list[dict[str, Any]]) -> str:
    bullets: list[str] = []
    for item in results[:3]:
        text = item.get("text", "").strip().replace("\n", " ")
        compact = " ".join(text.split())
        metadata = item.get("metadata", {}) or {}
        source = item.get("source_path", "unknown")
        suffix = []
        if metadata.get("topic"):
            suffix.append(f"topic={metadata['topic']}")
        bullets.append(f"- [{source}] {compact[:260]}...{' (' + ', '.join(suffix) + ')' if suffix else ''}")
    return "\n".join(bullets)
