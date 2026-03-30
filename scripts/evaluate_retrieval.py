from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from statistics import mean

from qdrant_client import QdrantClient

sys.path.insert(0, "/app")
from app.config import Settings  # noqa: E402
from app.rag.embeddings import build_embedding_provider  # noqa: E402

settings = Settings()
QDRANT_URL = os.getenv("QDRANT_URL", settings.qdrant_url)
COLLECTION = os.getenv("QDRANT_COLLECTION", settings.qdrant_collection)
EVAL_FILE = Path(os.getenv("EVAL_TESTSET_PATH", "/workspace/evaluation/testset.json"))
K = int(os.getenv("EVAL_K", str(settings.top_k)))


def precision_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    top_k = retrieved[:k]
    hits = sum(1 for item in top_k if any(item.startswith(g) for g in gold))
    return hits / max(k, 1)


def recall_at_k(retrieved: list[str], gold: list[str], k: int) -> float:
    top_k = retrieved[:k]
    hits = sum(1 for gold_item in gold if any(item.startswith(gold_item) for item in top_k))
    return hits / max(len(gold), 1)


def reciprocal_rank(retrieved: list[str], gold: list[str]) -> float:
    for idx, item in enumerate(retrieved, start=1):
        if any(item.startswith(g) for g in gold):
            return 1 / idx
    return 0.0


def load_testset() -> list[dict]:
    payload = json.loads(EVAL_FILE.read_text(encoding="utf-8"))
    return payload["questions"]


def main() -> None:
    client = QdrantClient(url=QDRANT_URL)
    embedder = build_embedding_provider(settings)
    tests = load_testset()
    details: list[dict] = []

    for test in tests:
        vector = embedder.embed_query(test["query"])
        hits = client.search(collection_name=COLLECTION, query_vector=vector, limit=max(K, 8))
        retrieved = [hit.payload.get("source_path", "") for hit in hits]
        details.append(
            {
                "id": test["id"],
                "query": test["query"],
                "route_expected": test.get("route_expected", []),
                "gold_sources": test["expected_sources"],
                "retrieved": retrieved,
                "precision_at_k": round(precision_at_k(retrieved, test["expected_sources"], K), 4),
                "recall_at_k": round(recall_at_k(retrieved, test["expected_sources"], K), 4),
                "mrr": round(reciprocal_rank(retrieved, test["expected_sources"]), 4),
            }
        )

    macro = {
        f"precision_at_{K}": round(mean(item["precision_at_k"] for item in details), 4),
        f"recall_at_{K}": round(mean(item["recall_at_k"] for item in details), 4),
        "mrr": round(mean(item["mrr"] for item in details), 4),
        "question_count": len(details),
        "embedding_model": f"{settings.embedding_provider}:{settings.embedding_model}",
        "chunk_size": settings.rag_chunk_size,
        "chunk_overlap": settings.rag_chunk_overlap,
        "top_k": K,
    }
    print(json.dumps({"macro": macro, "details": details}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
