import json
import sqlite3
from pathlib import Path


class SessionStore:
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
                CREATE TABLE IF NOT EXISTS agent_b_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message TEXT NOT NULL,
                    response_json TEXT NOT NULL
                )
                '''
            )
            conn.commit()

    def log(self, message: str, response: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO agent_b_requests (message, response_json) VALUES (?, ?)",
                (message, json.dumps(response, ensure_ascii=False)),
            )
            conn.commit()
