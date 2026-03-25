from __future__ import annotations

from app.retrieval.embeddings import HashEmbedding
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

    def retrieve(self, query: str, vector_store: MilvusLiteStore, limit: int = 3) -> list[dict]:
        query_vector = self.embedding.embed(query)
        return vector_store.search(query_vector, limit=limit)

