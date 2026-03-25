from __future__ import annotations

import json
import math
from pathlib import Path

try:
    from pymilvus import DataType, MilvusClient
except Exception:  # pragma: no cover - exercised through fallback mode.
    DataType = None
    MilvusClient = None

from app.retrieval.embeddings import HashEmbedding


class MilvusLiteStore:
    def __init__(
        self,
        db_path: str | Path,
        collection_name: str = "knowledge_chunks",
        dim: int = 64,
    ) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.dim = dim
        self.embedding = HashEmbedding(dim=dim)
        self.mode = "fallback"
        self.client = None
        self.fallback_path = self.db_path.with_suffix(".vectors.json")
        self._connect()

    def _connect(self) -> None:
        if MilvusClient is None or DataType is None:
            self._ensure_fallback_file()
            return
        try:
            self.client = MilvusClient(str(self.db_path))
            self._ensure_collection()
            self.mode = "milvus"
        except Exception:
            self.client = None
            self._ensure_fallback_file()

    def _ensure_fallback_file(self) -> None:
        if not self.fallback_path.exists():
            self.fallback_path.write_text("[]", encoding="utf-8")

    def _ensure_collection(self) -> None:
        if self.client is None:
            return
        if self.client.has_collection(self.collection_name):
            return

        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(field_name="file_id", datatype=DataType.INT64)
        schema.add_field(field_name="chunk_index", datatype=DataType.INT64)
        schema.add_field(field_name="source_path", datatype=DataType.VARCHAR, max_length=512)
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=4096)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.dim)

        index_params = self.client.prepare_index_params()
        index_params.add_index(field_name="vector", index_type="AUTOINDEX", metric_type="COSINE")

        self.client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )

    def upsert_file_chunks(self, file_id: int, source_path: str, chunks: list[str]) -> None:
        data = []
        for chunk_index, text in enumerate(chunks):
            record_id = file_id * 100000 + chunk_index
            data.append(
                {
                    "id": record_id,
                    "file_id": file_id,
                    "chunk_index": chunk_index,
                    "source_path": source_path,
                    "text": text[:4096],
                    "vector": self.embedding.embed(text),
                }
            )
        if not data:
            return
        if self.mode == "milvus" and self.client is not None:
            self.client.upsert(collection_name=self.collection_name, data=data)
            return

        existing = self._load_fallback_records()
        existing_by_id = {item["id"]: item for item in existing}
        for item in data:
            existing_by_id[item["id"]] = item
        self._write_fallback_records(list(existing_by_id.values()))

    def search(self, query_vector: list[float], limit: int = 3) -> list[dict]:
        if self.mode == "milvus" and self.client is not None:
            results = self.client.search(
                collection_name=self.collection_name,
                data=[query_vector],
                limit=limit,
                output_fields=["file_id", "chunk_index", "source_path", "text"],
            )
            hits = results[0] if results else []
            normalized = []
            for item in hits:
                entity = item.get("entity", {})
                normalized.append(
                    {
                        "file_id": entity.get("file_id"),
                        "chunk_index": entity.get("chunk_index"),
                        "source_path": entity.get("source_path"),
                        "text": entity.get("text"),
                        "score": item.get("distance", 0.0),
                    }
                )
            return normalized

        records = self._load_fallback_records()
        scored = []
        for item in records:
            score = self._cosine_similarity(query_vector, item["vector"])
            scored.append(
                {
                    "file_id": item["file_id"],
                    "chunk_index": item["chunk_index"],
                    "source_path": item["source_path"],
                    "text": item["text"],
                    "score": score,
                }
            )
        scored.sort(key=lambda row: row["score"], reverse=True)
        return scored[:limit]

    def _load_fallback_records(self) -> list[dict]:
        return json.loads(self.fallback_path.read_text(encoding="utf-8"))

    def _write_fallback_records(self, records: list[dict]) -> None:
        self.fallback_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _cosine_similarity(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left)) or 1.0
        right_norm = math.sqrt(sum(b * b for b in right)) or 1.0
        return numerator / (left_norm * right_norm)
