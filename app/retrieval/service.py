from __future__ import annotations

from typing import Any

from app.retrieval.embeddings import HashEmbedding
from app.storage.db import SQLiteStorage
from app.storage.vector_store import MilvusLiteStore


class RetrievalService:
    def __init__(self, embedding: HashEmbedding | None = None) -> None:
        self.embedding = embedding or HashEmbedding()

    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
        stripped = " ".join(text.split())
        if not stripped:
            return []
        chunks: list[str] = []
        start = 0
        text_length = len(stripped)
        while start < text_length:
            end = min(text_length, start + chunk_size)
            chunks.append(stripped[start:end])
            if end >= text_length:
                break
            start = max(0, end - overlap)
        return chunks

    def retrieve(
        self,
        query: str,
        vector_store: MilvusLiteStore,
        sqlite_storage: SQLiteStorage,
        *,
        limit: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        query_vector = self.embedding.embed(query)
        candidates = vector_store.search(query_vector, limit=max(limit * 5, 20))
        normalized_filters = self.normalize_filters(filters or {})
        results: list[dict] = []
        for candidate in candidates:
            chunk = sqlite_storage.get_file_chunk(candidate["id"]) if candidate.get("id") is not None else None
            merged = dict(candidate)
            if chunk:
                merged.update(
                    {
                        "source_name": chunk.get("source_name"),
                        "extension": chunk.get("extension"),
                        "media_type": chunk.get("media_type"),
                        "text": chunk.get("text", merged.get("text")),
                    }
                )
            if self.matches_filters(merged, normalized_filters):
                results.append(merged)
            if len(results) >= limit:
                break
        return results

    def normalize_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        normalized = {}
        for key, value in filters.items():
            if value in {"", None}:
                continue
            if key == "file_id":
                normalized[key] = int(value)
            else:
                normalized[key] = str(value).lower()
        return normalized

    def matches_filters(self, item: dict[str, Any], filters: dict[str, Any]) -> bool:
        if not filters:
            return True
        for key, expected in filters.items():
            actual = item.get(key)
            if key == "file_id":
                if actual != expected:
                    return False
                continue
            if actual is None or str(actual).lower() != expected:
                return False
        return True
