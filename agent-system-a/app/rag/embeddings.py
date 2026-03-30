from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

from app.config import Settings

try:
    from fastembed import TextEmbedding
except Exception:  # noqa: BLE001
    TextEmbedding = None  # type: ignore


class LocalDeterministicEmbeddings:
    TOKEN_RE = re.compile(r"[\w\u0600-\u06FF\-]+", flags=re.UNICODE)

    def __init__(self, dimension: int = 256) -> None:
        self.dimension = dimension

    def _tokenize(self, text: str) -> list[str]:
        normalized = text.replace("m²", "m2").replace("mÂ²", "m2").lower()
        tokens = self.TOKEN_RE.findall(normalized)
        bigrams = [f"{tokens[index]}__{tokens[index + 1]}" for index in range(len(tokens) - 1)]
        return tokens + bigrams

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
            if "__" in token:
                weight *= 1.15
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm > 0 else vector

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class FastEmbedAdapter:
    def __init__(self, model_name: str) -> None:
        if TextEmbedding is None:
            raise RuntimeError("fastembed is not installed")
        self.model_name = model_name
        self.model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        return [list(vec) for vec in self.model.embed(list(texts))]

    def embed_query(self, text: str) -> list[float]:
        return list(next(self.model.query_embed(text)))


def build_embedding_provider(settings: Settings):
    provider = settings.embedding_provider.lower().strip()
    if provider == "fastembed":
        try:
            return FastEmbedAdapter(settings.embedding_model)
        except Exception:
            return LocalDeterministicEmbeddings(dimension=settings.local_embedding_dimension)
    return LocalDeterministicEmbeddings(dimension=settings.local_embedding_dimension)
