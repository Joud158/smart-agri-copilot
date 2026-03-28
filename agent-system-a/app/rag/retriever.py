from __future__ import annotations

import os
from typing import Any

from qdrant_client import QdrantClient, models

from app.rag.embeddings import get_embedding_model


class QdrantRetriever:
    def __init__(
        self,
        url: str | None = None,
        collection_name: str | None = None,
        top_k: int = 5,
        timeout: int = 30,
    ) -> None:
        self.client = QdrantClient(
            url=url or os.getenv("QDRANT_URL", "http://vector-db:6333"),
            timeout=timeout,
        )
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION", "smart_agri_docs")
        self.top_k = top_k
        self.embedder = get_embedding_model()

    def _build_filter(self, filter_payload: dict[str, Any] | None) -> models.Filter | None:
        if not filter_payload:
            return None

        must_conditions: list[models.FieldCondition] = []

        for key, value in filter_payload.items():
            if value is None or value == "":
                continue

            if isinstance(value, list):
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchAny(any=value),
                    )
                )
            else:
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )

        if not must_conditions:
            return None

        return models.Filter(must=must_conditions)

    def search(
        self,
        query: str,
        filter_payload: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        query_vector = self.embedder.embed_query(query)
        qdrant_filter = self._build_filter(filter_payload)

        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
            limit=limit or self.top_k,
            with_payload=True,
            with_vectors=False,
        )

        points = getattr(response, "points", None)
        if points is None and hasattr(response, "result"):
            points = getattr(response.result, "points", [])

        results: list[dict[str, Any]] = []
        for point in points or []:
            payload = getattr(point, "payload", {}) or {}
            results.append(
                {
                    "id": getattr(point, "id", None),
                    "score": float(getattr(point, "score", 0.0) or 0.0),
                    "payload": payload,
                    "text": payload.get("text", ""),
                }
            )

        return results