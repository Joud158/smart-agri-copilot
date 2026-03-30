from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Iterable

import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.http import models as rest

# Make app imports work when script runs in container.
sys.path.insert(0, "/app")

from app.config import Settings  # noqa: E402
from app.rag.embeddings import build_embedding_provider  # noqa: E402

settings = Settings()
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/workspace/data"))
QDRANT_URL = os.getenv("QDRANT_URL", settings.qdrant_url)
COLLECTION = os.getenv("QDRANT_COLLECTION", settings.qdrant_collection)
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", str(settings.rag_chunk_size)))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", str(settings.rag_chunk_overlap)))
ALLOWED_SUFFIXES = {".md", ".txt", ".csv", ".pdf"}


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


def chunk_text(text: str) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n## ", "\n# ", "\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )
    return [chunk.strip() for chunk in splitter.split_text(text) if chunk.strip()]


def point_id(source_path: str, chunk_index: int) -> int:
    import hashlib
    digest = hashlib.sha256(f"{source_path}:{chunk_index}".encode("utf-8")).hexdigest()
    return int(digest[:15], 16)


def extract_pdf_pages(file_path: Path) -> list[tuple[str, dict[str, str]]]:
    doc = fitz.open(file_path)
    pages: list[tuple[str, dict[str, str]]] = []
    for index, page in enumerate(doc, start=1):
        text = page.get_text("text") or ""
        if text.strip():
            pages.append((text, {"page": str(index), "content_type": "pdf_page"}))
    return pages


def iter_documents() -> Iterable[tuple[Path, str, dict[str, str]]]:
    if not DATA_ROOT.exists():
        return
    for file_path in sorted(DATA_ROOT.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in ALLOWED_SUFFIXES:
            continue
        suffix = file_path.suffix.lower()
        if suffix in {".md", ".txt", ".csv"}:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            metadata = parse_metadata(text)
            metadata.update({"source_type": "base_doc", "content_type": suffix.lstrip(".")})
            yield file_path, text, metadata
        elif suffix == ".pdf":
            for page_text, page_meta in extract_pdf_pages(file_path):
                metadata = {"source_type": "base_doc", **page_meta}
                yield file_path, page_text, metadata


def main() -> None:
    client = QdrantClient(url=QDRANT_URL)
    embedder = build_embedding_provider(settings)
    documents: list[dict] = []

    for file_path, text, metadata in iter_documents():
        try:
            source_path = str(file_path.relative_to(DATA_ROOT))
        except Exception:
            source_path = file_path.name
        title = extract_title(text, file_path.stem.replace("_", " ").title())
        for index, chunk in enumerate(chunk_text(text)):
            payload = {"source_path": source_path, "title": title, "text": chunk, **metadata}
            documents.append({"id": point_id(f"{source_path}", index), "payload": payload})

    if not documents:
        raise RuntimeError("No corpus files found to index.")

    vectors = embedder.embed_documents([doc["payload"]["text"] for doc in documents])
    vector_size = len(vectors[0])

    if client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=rest.VectorParams(size=vector_size, distance=rest.Distance.COSINE),
    )

    points = [rest.PointStruct(id=doc["id"], vector=vector, payload=doc["payload"]) for doc, vector in zip(documents, vectors, strict=True)]
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"Indexed {len(points)} chunks into collection '{COLLECTION}' from {DATA_ROOT} using {settings.embedding_provider}:{settings.embedding_model}.")


if __name__ == "__main__":
    main()
