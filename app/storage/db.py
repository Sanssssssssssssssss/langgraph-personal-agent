from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path


class SQLiteStorage:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _managed_connection(self):
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._managed_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    due_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS preferences (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    source_name TEXT,
                    extension TEXT,
                    media_type TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS file_chunks (
                    id INTEGER PRIMARY KEY,
                    file_id INTEGER NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    source_path TEXT NOT NULL,
                    source_name TEXT,
                    extension TEXT,
                    media_type TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(file_id) REFERENCES files(id)
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    status TEXT NOT NULL,
                    awaiting_confirmation INTEGER NOT NULL,
                    pending_action TEXT,
                    show_trace INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS session_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    turn_index INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );

                CREATE TABLE IF NOT EXISTS session_snapshots (
                    session_id TEXT PRIMARY KEY,
                    preview TEXT,
                    message_count INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id)
                );
                """
            )
            self._ensure_column(conn, "files", "source_name", "TEXT")
            self._ensure_column(conn, "files", "extension", "TEXT")

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _normalize_session_record(self, row: sqlite3.Row | dict | None) -> dict | None:
        if row is None:
            return None
        record = dict(row)
        pending_action = record.get("pending_action")
        if isinstance(pending_action, str) and pending_action:
            record["pending_action"] = json.loads(pending_action)
        else:
            record["pending_action"] = None
        record["awaiting_confirmation"] = bool(record.get("awaiting_confirmation"))
        record["show_trace"] = bool(record.get("show_trace"))
        return record

    def _normalize_file_record(self, row: sqlite3.Row | dict | None) -> dict | None:
        if row is None:
            return None
        record = dict(row)
        original_path = record.get("original_path") or record.get("stored_path") or ""
        if original_path:
            path = Path(original_path)
            record["source_name"] = record.get("source_name") or path.name
            record["extension"] = record.get("extension") or path.suffix
        return record

    def create_note(self, title: str, content: str) -> dict:
        now = self._now()
        with self._managed_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO notes(title, content, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (title, content, now, now),
            )
            note_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
            return dict(row)

    def get_note(self, note_id: int) -> dict:
        with self._managed_connection() as conn:
            row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
            if row is None:
                raise ValueError(f"Note {note_id} not found")
            return dict(row)

    def list_notes(self) -> list[dict]:
        with self._managed_connection() as conn:
            rows = conn.execute("SELECT * FROM notes ORDER BY updated_at DESC").fetchall()
            return [dict(row) for row in rows]

    def search_notes(self, query: str) -> list[dict]:
        pattern = f"%{query}%"
        with self._managed_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? ORDER BY updated_at DESC",
                (pattern, pattern),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_note(self, note_id: int, title: str, content: str) -> dict:
        with self._managed_connection() as conn:
            conn.execute(
                "UPDATE notes SET title = ?, content = ?, updated_at = ? WHERE id = ?",
                (title, content, self._now(), note_id),
            )
            row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
            if row is None:
                raise ValueError(f"Note {note_id} not found")
            return dict(row)

    def delete_note(self, note_id: int) -> None:
        with self._managed_connection() as conn:
            conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))

    def create_reminder(self, content: str, due_at: str | None) -> dict:
        now = self._now()
        with self._managed_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO reminders(content, status, due_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (content, "pending", due_at, now, now),
            )
            reminder_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            return dict(row)

    def get_reminder(self, reminder_id: int) -> dict:
        with self._managed_connection() as conn:
            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            if row is None:
                raise ValueError(f"Reminder {reminder_id} not found")
            return dict(row)

    def list_reminders(self) -> list[dict]:
        with self._managed_connection() as conn:
            rows = conn.execute("SELECT * FROM reminders ORDER BY updated_at DESC").fetchall()
            return [dict(row) for row in rows]

    def update_reminder_status(self, reminder_id: int, status: str) -> dict:
        mapped = {"done": "done", "cancel": "cancelled"}
        with self._managed_connection() as conn:
            conn.execute(
                "UPDATE reminders SET status = ?, updated_at = ? WHERE id = ?",
                (mapped[status], self._now(), reminder_id),
            )
            row = conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone()
            if row is None:
                raise ValueError(f"Reminder {reminder_id} not found")
            return dict(row)

    def set_preference(self, key: str, value: str) -> dict:
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO preferences(key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, self._now()),
            )
            row = conn.execute("SELECT * FROM preferences WHERE key = ?", (key,)).fetchone()
            return dict(row) if row else {}

    def get_preference(self, key: str) -> dict | None:
        with self._managed_connection() as conn:
            row = conn.execute("SELECT * FROM preferences WHERE key = ?", (key,)).fetchone()
            return dict(row) if row else None

    def list_preferences(self) -> list[dict]:
        with self._managed_connection() as conn:
            rows = conn.execute("SELECT * FROM preferences ORDER BY key").fetchall()
            return [dict(row) for row in rows]

    def create_session(self, session_id: str, title: str | None, show_trace: bool) -> dict:
        now = self._now()
        with self._managed_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions(id, title, status, awaiting_confirmation, pending_action, show_trace, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, title, "active", 0, None, int(show_trace), now, now),
            )
            conn.execute(
                """
                INSERT INTO session_snapshots(session_id, preview, message_count, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, "", 0, now),
            )
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            return self._normalize_session_record(row) or {}

    def get_session(self, session_id: str) -> dict:
        with self._managed_connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
            if row is None:
                raise ValueError(f"Session {session_id} not found")
            return self._normalize_session_record(row) or {}

    def list_sessions(self, limit: int = 10) -> list[dict]:
        with self._managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*, ss.preview, ss.message_count
                FROM sessions s
                LEFT JOIN session_snapshots ss ON ss.session_id = s.id
                ORDER BY s.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [self._normalize_session_record(row) or {} for row in rows]

    def list_session_messages(self, session_id: str) -> list[dict]:
        with self._managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT turn_index, role, content, created_at
                FROM session_messages
                WHERE session_id = ?
                ORDER BY turn_index ASC, id ASC
                """,
                (session_id,),
            ).fetchall()
            return [dict(row) for row in rows]

    def save_session_state(
        self,
        session_id: str,
        *,
        title: str | None,
        messages: list[dict[str, str]],
        pending_confirmation: dict | None,
        show_trace: bool,
        preview_message_limit: int = 6,
    ) -> dict:
        now = self._now()
        preview_messages = messages[-preview_message_limit:] if preview_message_limit > 0 else messages
        preview = " | ".join(
            f"{message.get('role')}: {message.get('content', '')[:60]}"
            for message in preview_messages
        )
        with self._managed_connection() as conn:
            conn.execute(
                """
                UPDATE sessions
                SET title = ?, awaiting_confirmation = ?, pending_action = ?, show_trace = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    title,
                    int(bool(pending_confirmation)),
                    json.dumps(pending_confirmation, ensure_ascii=False) if pending_confirmation else None,
                    int(show_trace),
                    now,
                    session_id,
                ),
            )
            conn.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
            for index, message in enumerate(messages):
                conn.execute(
                    """
                    INSERT INTO session_messages(session_id, turn_index, role, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        index,
                        message.get("role", "assistant"),
                        message.get("content", ""),
                        now,
                    ),
                )
            conn.execute(
                """
                INSERT INTO session_snapshots(session_id, preview, message_count, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    preview = excluded.preview,
                    message_count = excluded.message_count,
                    updated_at = excluded.updated_at
                """,
                (session_id, preview, len(messages), now),
            )
            row = conn.execute(
                """
                SELECT s.*, ss.preview, ss.message_count
                FROM sessions s
                LEFT JOIN session_snapshots ss ON ss.session_id = s.id
                WHERE s.id = ?
                """,
                (session_id,),
            ).fetchone()
            return self._normalize_session_record(row) or {}

    def create_file(
        self,
        original_path: str,
        stored_path: str,
        source_name: str,
        extension: str,
        media_type: str,
        checksum: str,
        chunk_count: int,
    ) -> dict:
        with self._managed_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO files(original_path, stored_path, source_name, extension, media_type, checksum, chunk_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    original_path,
                    stored_path,
                    source_name,
                    extension,
                    media_type,
                    checksum,
                    chunk_count,
                    self._now(),
                ),
            )
            file_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
            return dict(row)

    def get_file(self, file_id: int) -> dict:
        with self._managed_connection() as conn:
            row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
            if row is None:
                raise ValueError(f"File {file_id} not found")
            return self._normalize_file_record(row) or {}

    def list_files(self) -> list[dict]:
        with self._managed_connection() as conn:
            rows = conn.execute("SELECT * FROM files ORDER BY created_at DESC").fetchall()
            return [self._normalize_file_record(row) or {} for row in rows]

    def upsert_file_chunks(
        self,
        file_id: int,
        source_path: str,
        source_name: str,
        extension: str,
        media_type: str,
        chunks: list[str],
    ) -> list[dict]:
        now = self._now()
        records = []
        with self._managed_connection() as conn:
            for chunk_index, text in enumerate(chunks):
                chunk_id = file_id * 100000 + chunk_index
                conn.execute(
                    """
                    INSERT INTO file_chunks(id, file_id, chunk_index, source_path, source_name, extension, media_type, text, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        file_id = excluded.file_id,
                        chunk_index = excluded.chunk_index,
                        source_path = excluded.source_path,
                        source_name = excluded.source_name,
                        extension = excluded.extension,
                        media_type = excluded.media_type,
                        text = excluded.text
                    """,
                    (
                        chunk_id,
                        file_id,
                        chunk_index,
                        source_path,
                        source_name,
                        extension,
                        media_type,
                        text,
                        now,
                    ),
                )
                records.append(
                    {
                        "id": chunk_id,
                        "file_id": file_id,
                        "chunk_index": chunk_index,
                        "source_path": source_path,
                        "source_name": source_name,
                        "extension": extension,
                        "media_type": media_type,
                        "text": text,
                    }
                )
        return records

    def get_file_chunk(self, chunk_id: int) -> dict | None:
        with self._managed_connection() as conn:
            row = conn.execute("SELECT * FROM file_chunks WHERE id = ?", (chunk_id,)).fetchone()
            return dict(row) if row else None

    def list_file_chunks(self, file_id: int, limit: int = 3) -> list[dict]:
        with self._managed_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM file_chunks
                WHERE file_id = ?
                ORDER BY chunk_index ASC
                LIMIT ?
                """,
                (file_id, limit),
            ).fetchall()
            return [dict(row) for row in rows]
