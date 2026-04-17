"""SQLite key-value style storage for memory metadata (legacy local mode)."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class KVStore:
    """SQLite-backed metadata store for memories."""

    def __init__(self, db_path: str = "unimem.db") -> None:
        self.db_path = db_path
        self._initialize()

    def _get_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._get_connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def save_memory(self, memory_id: str, user_id: str, content: str) -> dict:
        if not memory_id:
            raise ValueError("memory_id must not be empty")
        if not user_id:
            raise ValueError("user_id must not be empty")
        if not content.strip():
            raise ValueError("content must not be empty")

        created_at = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO memories (id, user_id, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (memory_id, user_id, content, created_at),
            )
            connection.commit()

        return {
            "id": memory_id,
            "user_id": user_id,
            "content": content,
            "created_at": created_at,
        }

    def get_memories_by_ids(self, memory_ids: list[str]) -> list[dict]:
        if not memory_ids:
            return []

        placeholders = ", ".join("?" for _ in memory_ids)
        query = f"""
            SELECT id, user_id, content, created_at
            FROM memories
            WHERE id IN ({placeholders})
        """

        with self._get_connection() as connection:
            rows = connection.execute(query, memory_ids).fetchall()

        row_map = {row["id"]: dict(row) for row in rows}
        return [row_map[memory_id] for memory_id in memory_ids if memory_id in row_map]

