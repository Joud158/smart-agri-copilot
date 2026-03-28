from __future__ import annotations

import re


KNOWN_CROPS = ["tomato", "olive", "wheat", "grape", "cucumber", "potato"]
KNOWN_REGIONS = ["bekaa", "coast", "mountain", "mountains", "lebanon"]
KNOWN_STAGES = ["flowering", "fruiting", "seedling", "vegetative", "harvest", "full_cycle"]


def extract_entities(message: str) -> tuple[str | None, str | None, str | None]:
    lowered = message.lower()

    crop = next((item for item in KNOWN_CROPS if item in lowered), None)
    region = next((item for item in KNOWN_REGIONS if item in lowered), None)
    stage = next((item for item in KNOWN_STAGES if item in lowered), None)

    return crop, region, stage


def decide_routes(message: str) -> list[str]:
    """Heuristic supervisor routing.

    A deterministic router is useful for demo reliability.
    If you later want to improve it, you can swap this function with a structured-LLM router
    without changing the graph wiring.
    """

    lowered = message.lower()
    routes: list[str] = []

    if any(word in lowered for word in ["plant", "crop", "grow", "harvest", "suitab", "region"]):
        routes.append("crop")

    if any(word in lowered for word in ["pest", "disease", "spots", "yellow", "sticky", "aphid", "whitefly", "powder"]):
        routes.append("pest")

    if any(word in lowered for word in ["price", "market", "sell", "hold", "storage"]):
        routes.append("market")

    if any(word in lowered for word in ["water", "irrigation", "frost", "spray timing"]):
        routes.append("irrigation")

    if any(word in lowered for word in ["soil", "ph", "fertilizer", "fertigation", "organic matter", "npk"]):
        routes.append("soil")

    if not routes:
        # Safe default: start with crop context because many questions anchor on the crop first.
        routes.append("crop")

    # Preserve order while removing duplicates.
    seen: set[str] = set()
    deduped: list[str] = []
    for item in routes:
        if item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped
