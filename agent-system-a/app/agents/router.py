from __future__ import annotations

from app.agents.parsing import ParsedMessage, decide_routes as decide_routes_from_parsed
from app.agents.parsing import merge_context, parse_message


def extract_entities(message: str, history: list[dict[str, str]] | None = None) -> ParsedMessage:
    parsed = parse_message(message)
    return merge_context(parsed, history)


def decide_routes(message: str, history: list[dict[str, str]] | None = None) -> list[str]:
    parsed = extract_entities(message, history)
    return decide_routes_from_parsed(message, parsed)
