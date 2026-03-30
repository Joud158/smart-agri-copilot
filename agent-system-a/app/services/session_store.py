from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path


class SessionStore:
    """SQLite-backed chat history with TTL cleanup and lightweight schema migration."""

    def __init__(self, db_path: str, ttl_hours: int = 24) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = max(ttl_hours, 1) * 3600
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _table_columns(self, conn: sqlite3.Connection, table_name: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        return {row[1] for row in rows}

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL
                )
                """
            )
            cols = self._table_columns(conn, "chat_sessions")
            if "updated_at" not in cols:
                conn.execute("ALTER TABLE chat_sessions ADD COLUMN updated_at REAL")
                conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE updated_at IS NULL", (time.time(),))
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at)")
            conn.commit()
        self.cleanup_expired()

    def _now(self) -> float:
        return time.time()

    def cleanup_expired(self) -> None:
        cutoff = self._now() - self.ttl_seconds
        with self._connect() as conn:
            conn.execute("DELETE FROM chat_sessions WHERE COALESCE(updated_at, 0) < ?", (cutoff,))
            conn.commit()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.save_history(session_id, [])
        return session_id

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        self.cleanup_expired()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT history_json, COALESCE(updated_at, 0) FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
            return []
        if row[1] < self._now() - self.ttl_seconds:
            with self._connect() as conn:
                conn.execute("DELETE FROM chat_sessions WHERE session_id = ?", (session_id,))
                conn.commit()
            return []
        return json.loads(row[0])

    def save_history(self, session_id: str, history: list[dict[str, str]]) -> None:
        payload = json.dumps(history, ensure_ascii=False)
        updated_at = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_sessions (session_id, history_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    history_json = excluded.history_json,
                    updated_at = excluded.updated_at
                """,
                (session_id, payload, updated_at),
            )
            conn.commit()
