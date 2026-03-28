from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path


class SessionStore:
    """Very small SQLite-backed session store.

    Why SQLite here?
    - it satisfies session persistence across requests
    - it keeps the demo self-contained
    - it avoids introducing another infrastructure dependency only for chat history
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    session_id TEXT PRIMARY KEY,
                    history_json TEXT NOT NULL
                )
                '''
            )
            conn.commit()

    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        self.save_history(session_id, [])
        return session_id

    def get_history(self, session_id: str) -> list[dict[str, str]]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT history_json FROM chat_sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cur.fetchone()
        if not row:
            return []
        return json.loads(row[0])

    def save_history(self, session_id: str, history: list[dict[str, str]]) -> None:
        payload = json.dumps(history, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                '''
                INSERT INTO chat_sessions (session_id, history_json)
                VALUES (?, ?)
                ON CONFLICT(session_id) DO UPDATE SET history_json = excluded.history_json
                ''',
                (session_id, payload),
            )
            conn.commit()
