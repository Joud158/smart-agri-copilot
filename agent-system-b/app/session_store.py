from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path


class SessionStore:
    """SQLite-backed session history plus lightweight request logging."""

    def __init__(self, db_path: str, ttl_hours: int = 24) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.ttl_seconds = max(ttl_hours, 1) * 3600
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_b_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    message TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON chat_sessions(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_b_requests_created_at ON agent_b_requests(created_at)")
            conn.commit()
        self.cleanup_expired()

    def _now(self) -> float:
        return time.time()

    def cleanup_expired(self) -> None:
        cutoff = self._now() - self.ttl_seconds
        with self._connect() as conn:
            conn.execute("DELETE FROM chat_sessions WHERE updated_at < ?", (cutoff,))
            conn.execute("DELETE FROM agent_b_requests WHERE created_at < ?", (cutoff,))
            conn.commit()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.save_history(session_id, [])
        return session_id

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        self.cleanup_expired()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT history_json FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if not row:
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

    def log(self, session_id: str | None, message: str, response: dict) -> None:
        self.cleanup_expired()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_b_requests (session_id, message, response_json, created_at) VALUES (?, ?, ?, ?)",
                (session_id, message, json.dumps(response, ensure_ascii=False), self._now()),
            )
            conn.commit()
