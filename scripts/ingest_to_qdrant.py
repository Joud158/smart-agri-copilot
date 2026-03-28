from __future__ import annotations

import hashlib
import math
import os
import re
from pathlib import Path
from typing import Iterable

from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

DATA_ROOT = Path("/workspace/data")
QDRANT_URL = os.getenv("QDRANT_URL", "http://vector-db:6333")
COLLECTION = os.getenv("QDRANT_COLLECTION", "smart_agri_docs")
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "650"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
EMBEDDING_DIMENSION = int(os.getenv("LOCAL_EMBEDDING_DIMENSION", "256"))


class LocalDeterministicEmbeddings:
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


def parse_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    match = re.search(r"## Metadata\n(.*?)(?:\n## |\Z)", text, flags=re.S)
    if not match:
        return metadata

    for line in match.group(1).splitlines():
        line = line.strip()
        if line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def split_markdown(text: str) -> list[str]:
    sections = re.split(r"\n(?=##?\s)", text)
    chunks: list[str] = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        if len(section) <= CHUNK_SIZE:
            chunks.append(section)
            continue

        start = 0
        while start < len(section):
            end = start + CHUNK_SIZE
            chunk = section[start:end]
            chunks.append(chunk)
            if end >= len(section):
                break
            start = end - CHUNK_OVERLAP

    return chunks


def point_id(source_path: str, chunk_index: int) -> int:
    digest = hashlib.sha256(f"{source_path}:{chunk_index}".encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def main() -> None:
    client = QdrantClient(url=QDRANT_URL)
    embedder = LocalDeterministicEmbeddings(dimension=EMBEDDING_DIMENSION)
    documents: list[dict] = []

    for file_path in sorted(DATA_ROOT.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in {".md", ".csv"}:
            continue

        text = file_path.read_text(encoding="utf-8")
        title = extract_title(text, file_path.stem.replace("_", " ").title())
        metadata = parse_metadata(text)
        source_path = str(file_path.relative_to(DATA_ROOT))

        for index, chunk in enumerate(split_markdown(text)):
            payload = {
                "source_path": source_path,
                "title": title,
                "text": chunk,
                **metadata,
            }
            documents.append({"id": point_id(source_path, index), "payload": payload})

    if not documents:
        raise RuntimeError("No corpus files found to index.")

    vectors = embedder.embed_documents([doc["payload"]["text"] for doc in documents])
    vector_size = len(vectors[0])

    client.recreate_collection(
        collection_name=COLLECTION,
        vectors_config=rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE),
    )

    points = [
        rest.PointStruct(id=doc["id"], vector=vector, payload=doc["payload"])
        for doc, vector in zip(documents, vectors, strict=True)
    ]
    client.upsert(collection_name=COLLECTION, points=points)

    print(f"Indexed {len(points)} chunks into collection '{COLLECTION}' from {DATA_ROOT} using local deterministic embeddings.")


if __name__ == "__main__":
    main()
