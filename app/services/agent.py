from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.graph.builder import build_graph
from app.observability.tracer import TraceLogger
from app.retrieval.service import RetrievalService
from app.storage.db import SQLiteStorage
from app.storage.files import FileStorage
from app.storage.vector_store import MilvusLiteStore
from app.tools.registry import ToolRegistry


class PersonalAgent:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parents[2]
        self.data_dir = self.base_dir / "data"
        self.sqlite_storage = SQLiteStorage(self.data_dir / "processed" / "personal_agent.db")
        self.file_storage = FileStorage(self.data_dir / "uploads")
        self.vector_store = MilvusLiteStore(self.data_dir / "processed" / "personal_agent_milvus.db")
        self.retrieval_service = RetrievalService()
        self.tool_registry = ToolRegistry(
            sqlite_storage=self.sqlite_storage,
            file_storage=self.file_storage,
            vector_store=self.vector_store,
            retrieval_service=self.retrieval_service,
        )
        self.graph = build_graph(self.tool_registry)
        self.tracer = TraceLogger(self.data_dir / "benchmarks" / "trace.log")

    def invoke(self, user_input: str) -> dict:
        initial_state = {
            "request_id": str(uuid4()),
            "user_input": user_input,
            "context": {},
            "tool_calls": [],
            "memory_ops": [],
            "errors": [],
            "trace": [],
        }
        final_state = self.graph.invoke(initial_state)
        self.tracer.log(final_state)
        return final_state

