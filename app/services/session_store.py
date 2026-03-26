from __future__ import annotations

from typing import Any, TypedDict
from uuid import uuid4

from app.storage.db import SQLiteStorage


class PersistedSession(TypedDict, total=False):
    session_id: str
    title: str | None
    messages: list[dict[str, str]]
    pending_confirmation: dict[str, Any] | None
    show_trace: bool
    persisted: bool


class SessionStore:
    def __init__(self, sqlite_storage: SQLiteStorage, preview_message_limit: int = 6) -> None:
        self.sqlite_storage = sqlite_storage
        self.preview_message_limit = preview_message_limit

    def create_session(
        self,
        *,
        title: str | None = None,
        show_trace: bool = False,
        session_id: str | None = None,
    ) -> PersistedSession:
        session_id = session_id or str(uuid4())
        self.sqlite_storage.create_session(session_id, title, show_trace)
        return {
            "session_id": session_id,
            "title": title,
            "messages": [],
            "pending_confirmation": None,
            "show_trace": show_trace,
            "persisted": True,
        }

    def load_session(self, session_id: str) -> PersistedSession:
        record = self.sqlite_storage.get_session(session_id)
        messages = self.sqlite_storage.list_session_messages(session_id)
        return {
            "session_id": record["id"],
            "title": record.get("title"),
            "messages": [
                {"role": message["role"], "content": message["content"]}
                for message in messages
            ],
            "pending_confirmation": record.get("pending_action"),
            "show_trace": record.get("show_trace", False),
            "persisted": True,
        }

    def save_session(self, session: PersistedSession) -> PersistedSession:
        session_id = session["session_id"]
        record = self.sqlite_storage.save_session_state(
            session_id,
            title=session.get("title"),
            messages=list(session.get("messages", [])),
            pending_confirmation=session.get("pending_confirmation"),
            show_trace=session.get("show_trace", False),
            preview_message_limit=self.preview_message_limit,
        )
        return {
            "session_id": record["id"],
            "title": record.get("title"),
            "messages": list(session.get("messages", [])),
            "pending_confirmation": record.get("pending_action"),
            "show_trace": record.get("show_trace", False),
            "persisted": True,
        }

    def list_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.sqlite_storage.list_sessions(limit=limit)
