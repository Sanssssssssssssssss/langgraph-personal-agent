from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict
from uuid import uuid4

from app.graph.builder import build_graph
from app.observability.tracer import TraceLogger
from app.retrieval.service import RetrievalService
from app.settings import load_settings, resolve_path
from app.services.session_store import SessionStore
from app.storage.db import SQLiteStorage
from app.storage.files import FileStorage
from app.storage.vector_store import MilvusLiteStore
from app.tools.registry import ToolRegistry


class AgentSession(TypedDict, total=False):
    session_id: str
    title: str | None
    messages: list[dict[str, str]]
    pending_confirmation: dict[str, Any] | None
    show_trace: bool
    persisted: bool


class PersonalAgent:
    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).resolve().parents[2]
        self.settings = load_settings(self.base_dir)
        self.sqlite_storage = SQLiteStorage(
            resolve_path(self.base_dir, self.settings.storage.sqlite_path)
        )
        self.file_storage = FileStorage(
            resolve_path(self.base_dir, self.settings.storage.upload_dir)
        )
        self.vector_store = MilvusLiteStore(
            resolve_path(self.base_dir, self.settings.storage.milvus_path)
        )
        self.retrieval_service = RetrievalService()
        self.tool_registry = ToolRegistry(
            sqlite_storage=self.sqlite_storage,
            file_storage=self.file_storage,
            vector_store=self.vector_store,
            retrieval_service=self.retrieval_service,
            destructive_actions=self.settings.confirmation.destructive_actions,
        )
        self.graph = build_graph(self.tool_registry)
        self.session_store = SessionStore(
            self.sqlite_storage,
            preview_message_limit=self.settings.session.preview_message_limit,
        )
        self.tracer = TraceLogger(
            resolve_path(self.base_dir, self.settings.runtime.trace_path)
        )

    def new_session(
        self,
        *,
        show_trace: bool = False,
        persist: bool = False,
        title: str | None = None,
        session_id: str | None = None,
    ) -> AgentSession:
        session: AgentSession = {
            "messages": [],
            "pending_confirmation": None,
            "show_trace": show_trace,
            "persisted": persist,
        }
        if persist:
            session.update(
                self.session_store.create_session(
                    title=title,
                    show_trace=show_trace,
                    session_id=session_id,
                )
            )
        return session

    def load_session(self, session_id: str) -> AgentSession:
        return self.session_store.load_session(session_id)

    def list_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.session_store.list_sessions(limit=limit)

    def _normalize_session(self, session: AgentSession | None) -> AgentSession:
        normalized = self.new_session()
        if session:
            normalized["session_id"] = session.get("session_id", "")
            normalized["title"] = session.get("title")
            normalized["messages"] = list(session.get("messages", []))
            normalized["pending_confirmation"] = session.get("pending_confirmation")
            normalized["show_trace"] = session.get("show_trace", False)
            normalized["persisted"] = session.get("persisted", False)
        return normalized

    def _build_next_session(
        self,
        session: AgentSession,
        user_input: str,
        final_state: dict[str, Any],
    ) -> AgentSession:
        messages = list(session.get("messages", []))
        messages.append({"role": "user", "content": user_input})
        messages.append({"role": "assistant", "content": final_state.get("response", "")})
        return {
            "session_id": session.get("session_id", ""),
            "title": session.get("title"),
            "messages": messages,
            "pending_confirmation": final_state.get("pending_action")
            if final_state.get("awaiting_confirmation")
            else None,
            "show_trace": session.get("show_trace", False),
            "persisted": session.get("persisted", False),
        }

    def invoke(self, user_input: str, session: AgentSession | None = None) -> dict:
        normalized_session = self._normalize_session(session)
        initial_state = {
            "request_id": str(uuid4()),
            "session_id": normalized_session.get("session_id", ""),
            "user_input": user_input,
            "context": {},
            "messages": normalized_session.get("messages", []),
            "awaiting_confirmation": bool(normalized_session.get("pending_confirmation")),
            "pending_action": normalized_session.get("pending_confirmation"),
            "confirmation_prompt": "",
            "confirmation_response": "",
            "tool_calls": [],
            "memory_ops": [],
            "errors": [],
            "trace": [],
        }
        final_state = self.graph.invoke(initial_state)
        final_state["session"] = self._build_next_session(
            normalized_session, user_input, final_state
        )
        if final_state["session"].get("persisted") and final_state["session"].get("session_id"):
            final_state["session"] = self.session_store.save_session(final_state["session"])
        self.tracer.log(final_state)
        return final_state
