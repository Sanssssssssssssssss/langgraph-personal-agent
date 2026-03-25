from __future__ import annotations

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
                    media_type TEXT NOT NULL,
                    checksum TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

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

    def create_file(
        self,
        original_path: str,
        stored_path: str,
        media_type: str,
        checksum: str,
        chunk_count: int,
    ) -> dict:
        with self._managed_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO files(original_path, stored_path, media_type, checksum, chunk_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (original_path, stored_path, media_type, checksum, chunk_count, self._now()),
            )
            file_id = cursor.lastrowid
            row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
            return dict(row)
