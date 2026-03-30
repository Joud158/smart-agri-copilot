from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import mean
from typing import Any

import httpx

API_URL = os.getenv("AGENT_A_CHAT_URL", "http://agent-system-a:8101/chat")
TESTSET_PATH = Path(os.getenv("EVAL_TESTSET_PATH", "/workspace/evaluation/testset.json"))
MODE = os.getenv("GENERATION_EVAL_MODE", "heuristic").lower().strip()
TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "25"))


def load_testset() -> list[dict[str, Any]]:
    payload = json.loads(TESTSET_PATH.read_text(encoding="utf-8"))
    return payload["questions"]


def normalize(text: str) -> str:
    return " ".join(text.lower().replace("m²", "m2").split())


def overlap_score(reference: str, candidate: str) -> float:
    ref_tokens = {token for token in normalize(reference).split() if len(token) > 2}
    cand_tokens = {token for token in normalize(candidate).split() if len(token) > 2}
    if not ref_tokens:
        return 0.0
    return len(ref_tokens & cand_tokens) / len(ref_tokens)


def citation_score(expected_sources: list[str], actual_sources: list[str]) -> float:
    if not expected_sources:
        return 0.0
    hits = sum(1 for expected in expected_sources if any(src.startswith(expected) for src in actual_sources))
    return hits / len(expected_sources)


def evaluate_one(client: httpx.Client, item: dict[str, Any]) -> dict[str, Any]:
    response = client.post(API_URL, json={"message": item["query"]})
    response.raise_for_status()
    payload = response.json()
    answer = payload.get("answer", "")
    actual_sources = [src.get("source_path", "") for src in payload.get("sources", [])]
    expected_answer = item["ground_truth_answer"]

    faithfulness = round(citation_score(item["expected_sources"], actual_sources), 4)
    correctness = round(overlap_score(expected_answer, answer), 4)
    relevance = round(min(1.0, (correctness * 0.7) + (faithfulness * 0.3)), 4)

    result = {
        "id": item["id"],
        "query": item["query"],
        "mode": MODE,
        "route_expected": item.get("route_expected", []),
        "route_actual": payload.get("route", []),
        "faithfulness": faithfulness,
        "correctness": correctness,
        "relevance": relevance,
        "expected_sources": item["expected_sources"],
        "actual_sources": actual_sources,
        "answer_preview": answer[:240],
    }

    if MODE == "heuristic":
        result["judge_note"] = "Heuristic fallback based on answer overlap and evidence coverage. Switch GENERATION_EVAL_MODE to llm_judge if you wire in a judge model."
    else:
        result["judge_note"] = "LLM judge mode placeholder currently falls back to the heuristic scorer in this packaged build."
    return result


def main() -> None:
    tests = load_testset()
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        details = [evaluate_one(client, item) for item in tests]

    macro = {
        "question_count": len(details),
        "mode": MODE,
        "faithfulness": round(mean(item["faithfulness"] for item in details), 4),
        "correctness": round(mean(item["correctness"] for item in details), 4),
        "relevance": round(mean(item["relevance"] for item in details), 4),
    }
    print(json.dumps({"macro": macro, "details": details}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
