from __future__ import annotations

import json
import logging

from fastapi import FastAPI
from fastapi.responses import ORJSONResponse

from app.adk_agent import ADKRuntime, ADK_AVAILABLE
from app.config import get_settings
from app.domain_logic import build_irrigation_answer
from app.models import AgentBRequest, AgentBResponse
from app.session_store import SessionStore


def _configure_logger() -> logging.Logger:
    logger = logging.getLogger("agent-system-b")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def _log_event(logger: logging.Logger, event: str, **payload) -> None:
    logger.info(json.dumps({"event": event, **payload}, ensure_ascii=False, default=str))


settings = get_settings()
logger = _configure_logger()
session_store = SessionStore(settings.session_db_path, ttl_hours=settings.session_ttl_hours)
adk_runtime = ADKRuntime()

app = FastAPI(title=settings.app_name, version="2.1.0", default_response_class=ORJSONResponse)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "adk_available": str(ADK_AVAILABLE).lower(),
        "configured_mode": settings.agent_mode,
    }


@app.post("/chat", response_model=AgentBResponse)
async def chat(request: AgentBRequest) -> AgentBResponse:
    requested_mode = settings.agent_mode.lower().strip()
    session_id = request.session_id or session_store.create_session()
    history = session_store.get_history(session_id)

    selected_mode = "deterministic"
    runtime_note = "Deterministic irrigation logic used for reliability."
    answer = None

    can_try_adk = requested_mode in {"adk", "auto"} and ADK_AVAILABLE
    if can_try_adk:
        try:
            answer = await adk_runtime.run_turn(request.message, session_id=session_id)
            selected_mode = "adk"
            runtime_note = "Google ADK runner executed successfully."
        except Exception as exc:  # noqa: BLE001
            selected_mode = "deterministic_fallback"
            runtime_note = f"ADK path failed with {type(exc).__name__}; deterministic fallback used."

    deterministic_result = build_irrigation_answer(request.message, request.metadata)
    if answer is None:
        answer = deterministic_result["answer"]

    deterministic_result["answer"] = answer
    deterministic_result["mode"] = selected_mode
    deterministic_result["session_id"] = session_id
    deterministic_result.setdefault("structured_result", {})["agent_runtime"] = {
        "requested_mode": requested_mode,
        "selected_mode": selected_mode,
        "adk_available": ADK_AVAILABLE,
        "note": runtime_note,
        "history_turns_seen": len(history),
    }

    history.append({"role": "user", "content": request.message})
    history.append({"role": "assistant", "content": answer})
    session_store.save_history(session_id, history)
    session_store.log(session_id, request.message, deterministic_result)
    _log_event(
        logger,
        "agent_b_request_completed",
        requested_mode=requested_mode,
        selected_mode=selected_mode,
        session_id=session_id,
        message=request.message[:300],
    )

    return AgentBResponse(**deterministic_result)
