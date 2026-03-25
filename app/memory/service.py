from __future__ import annotations

from app.storage.db import SQLiteStorage


class MemoryService:
    def __init__(self, sqlite_storage: SQLiteStorage) -> None:
        self.sqlite_storage = sqlite_storage

