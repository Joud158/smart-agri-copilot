from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import Iterable


class LocalDeterministicEmbeddings:
    """Small offline embedding model used only for demo reliability.

    Why this exists:
    - avoids network calls and API quota limits
    - produces deterministic vectors so ingestion and retrieval stay aligned
    - keeps the Qdrant pipeline working for the project demo

    This is not semantically as strong as a production embedding API, but it is
    stable, explainable, and enough for a class project demo on a constrained
    connection.
    """

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = self._tokenize(text)
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.0 + (digest[5] / 255.0) * 0.25
            vector[index] += sign * weight

        norm = math.sqrt(sum(value * value for value in vector))
        if norm > 0:
            vector = [value / norm for value in vector]
        return vector

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


@lru_cache(maxsize=1)
def get_embedding_model() -> LocalDeterministicEmbeddings:
    """Return one cached local embedding model instance."""

    return LocalDeterministicEmbeddings(dimension=256)
