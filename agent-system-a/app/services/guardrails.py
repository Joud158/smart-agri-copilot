from __future__ import annotations

import re
from dataclasses import dataclass


DISCLAIMER = (
    "This assistant is for decision support only. It does not replace a certified agronomist, "
    "local field inspection, or laboratory soil / plant testing."
)

BLOCKED_PATTERNS = [
    re.compile(r"\bweapon\b", re.I),
    re.compile(r"\bexplosive\b", re.I),
    re.compile(r"\bmalware\b", re.I),
]

AGRI_HINTS = [
    "crop",
    "soil",
    "irrigation",
    "water",
    "watering",
    "fertilizer",
    "market",
    "price",
    "sell",
    "pest",
    "disease",
    "greenhouse",
    "field",
    "harvest",
    "bekaa",
    "tomato",
    "olive",
    "wheat",
    "grape",
    "cucumber",
    "طماطم", "زيتون", "قمح", "ري", "تربة", "سماد", "آفات",
    "tomate", "olivier", "blé", "irrigation", "sol", "engrais", "maladie",
]


@dataclass
class GuardrailResult:
    allowed: bool
    message: str | None = None


def check_input_scope(message: str, allow_out_of_domain: bool = False) -> GuardrailResult:
    """Perform lightweight input checks.

    We use a deterministic guardrail here because:
    - it is reliable
    - it is explainable
    - it works even when the LLM is unavailable
    """

    stripped = message.strip()

    for pattern in BLOCKED_PATTERNS:
        if pattern.search(stripped):
            return GuardrailResult(
                allowed=False,
                message="This system is limited to agriculture decision-support tasks.",
            )

    if allow_out_of_domain:
        return GuardrailResult(allowed=True)

    normalized = stripped.lower()
    if not any(hint in normalized for hint in AGRI_HINTS):
        return GuardrailResult(
            allowed=False,
            message=(
                "Please ask an agriculture-related question about crops, pests, irrigation, soil, "
                "fertilizer, or seasonal market guidance."
            ),
        )

    return GuardrailResult(allowed=True)


def apply_output_guardrail(answer: str) -> str:
    """Ensure every final answer keeps the intended scope visible."""

    cleaned = answer.strip()
    if DISCLAIMER not in cleaned:
        cleaned += f"\n\n**Disclaimer:** {DISCLAIMER}"
    return cleaned
