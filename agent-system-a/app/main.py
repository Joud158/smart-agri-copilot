from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.agents.graph import FarmAdvisorGraph
from app.config import get_settings
from app.models.api import ChatRequest, ChatResponse, ErrorResponse, HealthResponse, SourceSnippet
from app.rag.retriever import QdrantRetriever
from app.services.guardrails import DISCLAIMER, check_input_scope
from app.services.http_clients import ServiceClients
from app.services.llm_factory import build_chat_model
from app.services.logging_utils import configure_logging, log_event
from app.services.session_store import SessionStore

settings = get_settings()
logger = configure_logging("agent-system-a")
session_store = SessionStore(settings.session_db_path, ttl_hours=settings.session_ttl_hours)
retriever = QdrantRetriever(settings)
clients = ServiceClients(settings)
chat_model = None
if settings.enable_llm_synthesis:
    try:
        chat_model = build_chat_model(settings)
    except Exception as exc:  # noqa: BLE001
        log_event(logger, "llm_synthesis_init_failed", error=type(exc).__name__, provider=settings.llm_provider)
        chat_model = None
farm_graph = FarmAdvisorGraph(retriever=retriever, clients=clients, settings=settings, chat_model=chat_model)

app = FastAPI(title=settings.app_name, version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list or ["http://localhost:3000"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Token"],
)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


@app.post("/chat", response_model=ChatResponse, responses={400: {"model": ErrorResponse}})
async def chat(request: ChatRequest) -> ChatResponse:
    guardrail = check_input_scope(request.message, allow_out_of_domain=settings.allow_out_of_domain)
    if not guardrail.allowed:
        log_event(logger, "request_blocked", reason=guardrail.message, message=request.message[:200])
        raise HTTPException(status_code=400, detail=guardrail.message)

    session_id = request.session_id or session_store.create_session()
    history = session_store.get_history(session_id)
    log_event(
        logger,
        "chat_request_received",
        session_id=session_id,
        message=request.message[:500],
        history_len=len(history),
        stream=request.stream,
    )

    initial_state = {
        "session_id": session_id,
        "message": request.message,
        "history": history,
        "debug_trace": [],
    }

    result = await farm_graph.answer(initial_state)

    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": result["final_answer"]})
    session_store.save_history(session_id, history)

    sources = [
        SourceSnippet(
            source_path=item.get("source_path", "unknown"),
            title=item.get("title", "Untitled"),
            score=float(item.get("score", 0.0)),
            text=item.get("text", ""),
            metadata=item.get("metadata", {}),
        )
        for item in result.get("final_sources", [])
    ]

    response = ChatResponse(
        session_id=session_id,
        route=result.get("route", []),
        answer=result["final_answer"],
        disclaimer=DISCLAIMER,
        sources=sources,
        debug_trace=result.get("debug_trace", []),
    )
    log_event(
        logger,
        "chat_request_completed",
        session_id=session_id,
        route=response.route,
        source_count=len(response.sources),
        answer_preview=response.answer[:300],
    )
    return response


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest) -> StreamingResponse:
    response = await chat(request)

    async def event_generator() -> AsyncGenerator[str, None]:
        meta_payload = {"session_id": response.session_id, "route": response.route}
        yield f"event: meta\ndata: {json.dumps(meta_payload)}\n\n"

        words = response.answer.split()
        chunk: list[str] = []
        for index, word in enumerate(words, start=1):
            chunk.append(word)
            if index % 14 == 0:
                yield f"event: token\ndata: {json.dumps({'text': ' '.join(chunk) + ' '})}\n\n"
                chunk = []
                await asyncio.sleep(0.02)

        if chunk:
            yield f"event: token\ndata: {json.dumps({'text': ' '.join(chunk)})}\n\n"

        yield f"event: done\ndata: {json.dumps(response.model_dump())}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/admin/reindex")
async def admin_reindex(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict[str, str]:
    if not settings.admin_api_token or x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=403, detail="Admin token missing or invalid.")

    log_event(logger, "admin_reindex_hint_requested")
    return {
        "status": "ok",
        "message": "Run `python /app/scripts/ingest_to_qdrant.py` inside the container to reindex the corpus.",
    }
