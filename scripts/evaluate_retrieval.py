from __future__ import annotations

import json
import os

from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "smart_agri_docs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "replace_me")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

TESTS = [
    {"query": "Tomato flowering irrigation sensitivity", "gold": ["crops/01_fao_tomato_crop_info.md"]},
    {"query": "Greenhouse hygiene and sticky traps", "gold": ["pests/01_fao_ipm_protected_cultivation.md"]},
    {"query": "How pH affects nutrient availability", "gold": ["soil_fertilizer/06_fao_soil_fertility_plant_nutrition.md", "soil_fertilizer/01_curated_soil_ph_basics.md"]},
    {"query": "Harvest or hold decision rules for perishable crops", "gold": ["market/05_curated_harvest_or_hold_rules.md"]},
]


def precision_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if any(item.startswith(g) for g in gold))
    return hits / max(k, 1)


def recall_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    top_k = retrieved[:k]
    hits = sum(1 for gold_item in gold if any(item.startswith(gold_item) for item in top_k))
    return hits / max(len(gold), 1)


def mrr(retrieved: list[str], gold: list[str]) -> float:
    for idx, item in enumerate(retrieved, start=1):
        if any(item.startswith(g) for g in gold):
            return 1 / idx
    return 0.0


def main() -> None:
    client = QdrantClient(url=QDRANT_URL)
    embedder = OpenAIEmbeddings(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        model=EMBEDDING_MODEL,
    )

    scores = []
    for test in TESTS:
        vector = embedder.embed_query(test["query"])
        hits = client.search(collection_name=COLLECTION, query_vector=vector, limit=6)
        retrieved = [hit.payload.get("source_path", "") for hit in hits]

        scores.append(
            {
                "query": test["query"],
                "p_at_4": precision_at_k(retrieved, test["gold"], 4),
                "r_at_4": recall_at_k(retrieved, test["gold"], 4),
                "mrr": mrr(retrieved, test["gold"]),
                "retrieved": retrieved,
                "gold": test["gold"],
            }
        )

    macro = {
        "precision_at_4": round(sum(item["p_at_4"] for item in scores) / len(scores), 3),
        "recall_at_4": round(sum(item["r_at_4"] for item in scores) / len(scores), 3),
        "mrr": round(sum(item["mrr"] for item in scores) / len(scores), 3),
    }

    print(json.dumps({"macro": macro, "details": scores}, indent=2))


if __name__ == "__main__":
    main()
