from __future__ import annotations
import math
import re
from typing import Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.config import Settings
from app.rag.embeddings import build_embedding_provider


class QdrantRetriever:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = QdrantClient(url=settings.qdrant_url, timeout=settings.request_timeout_seconds)
        self.collection_name = settings.qdrant_collection
        self.top_k = settings.top_k
        self.fetch_k = max(settings.rag_fetch_k, self.top_k)
        self.embedder = build_embedding_provider(settings)

    def _build_filter(self, filter_payload: dict[str, Any] | None) -> models.Filter | None:
        if not filter_payload:
            return None
        clauses: list[models.FieldCondition] = []
        for key, value in filter_payload.items():
            if value is None:
                continue
            if isinstance(value, list):
                clauses.append(models.FieldCondition(key=key, match=models.MatchAny(any=value)))
            else:
                clauses.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
        return models.Filter(must=clauses) if clauses else None

    def _normalize_point(self, point: Any) -> dict[str, Any]:
        payload = dict(getattr(point, "payload", {}) or {})
        score = float(getattr(point, "score", 0.0) or 0.0)
        metadata = {
            key: value for key, value in payload.items()
            if key not in {"source_path", "title", "text"}
        }
        return {
            "source_path": payload.get("source_path", "unknown"),
            "title": payload.get("title", "Untitled"),
            "text": payload.get("text", ""),
            "score": score,
            "metadata": metadata,
            "payload": payload,
        }

    def _keyword_score(self, query: str, text: str, metadata: dict[str, Any]) -> float:
        q_tokens = re.findall(r"[\w\u0600-\u06FF\-]+", query.lower())
        if not q_tokens:
            return 0.0
        hay = f"{text} {' '.join(f'{k}:{v}' for k,v in metadata.items())}".lower()
        hits = sum(1 for token in set(q_tokens) if token in hay)
        coverage = hits / max(len(set(q_tokens)), 1)
        phrase_bonus = 0.15 if query.lower() in hay else 0.0
        return coverage + phrase_bonus

    def rerank(self, query: str, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not results:
            return results
        if self.settings.reranker_mode == "none":
            return results[: self.top_k]

        rescored: list[tuple[float, dict[str, Any]]] = []
        for item in results:
            semantic = float(item.get("score", 0.0))
            lexical = self._keyword_score(query, item.get("text", ""), item.get("metadata", {}))
            combined = (semantic * 0.75) + (lexical * 0.25)
            updated = dict(item)
            updated["metadata"] = dict(item.get("metadata", {}), rerank_semantic=round(semantic, 4), rerank_lexical=round(lexical, 4))
            updated["score"] = round(combined, 4)
            rescored.append((combined, updated))
        rescored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in rescored[: self.top_k]]

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
            limit=limit or self.fetch_k,
            with_payload=True,
            with_vectors=False,
        )

        points = getattr(response, "points", None)
        if points is None and hasattr(response, "result"):
            points = getattr(response.result, "points", [])
        normalized = [self._normalize_point(point) for point in (points or [])]
        return self.rerank(query, normalized)

    def max_score(self, results: list[dict[str, Any]]) -> float:
        return max((float(item.get("score", 0.0)) for item in results), default=0.0)

    def should_use_external_fallback(self, results: list[dict[str, Any]]) -> bool:
        if not results:
            return True
        best = self.max_score(results)
        return best < 0.42
