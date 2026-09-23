"""SQLite history of the last N analyses (per user)."""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    owner      TEXT    NOT NULL,
    file_name  TEXT    NOT NULL,
    created_at TEXT    NOT NULL,
    data_json  TEXT    NOT NULL,
    pdf        BLOB
)
"""


class HistoryStore:
    def __init__(self, db_path: str | Path, limit: int = 10):
        self.db_path = str(db_path)
        self.limit = limit

    def _connect(self) -> sqlite3.Connection:
        # Creating the table on every connection keeps the store working even if
        # the database file is deleted while the app is running.
        conn = sqlite3.connect(self.db_path)
        conn.execute(SCHEMA)
        return conn

    def add(self, owner: str, file_name: str, data: dict[str, Any], pdf: bytes | None) -> int:
        """Save an analysis and drop the oldest ones beyond ``limit``."""
        now = datetime.now().isoformat(timespec="seconds")
        with closing(self._connect()) as conn, conn:
            cur = conn.execute(
                "INSERT INTO analyses (owner, file_name, created_at, data_json, pdf) VALUES (?, ?, ?, ?, ?)",
                (owner, file_name, now, json.dumps(data, ensure_ascii=False), pdf),
            )
            conn.execute(
                """DELETE FROM analyses WHERE owner = ? AND id NOT IN (
                       SELECT id FROM analyses WHERE owner = ? ORDER BY id DESC LIMIT ?)""",
                (owner, owner, self.limit),
            )
            return int(cur.lastrowid)

    def list(self, owner: str, search: str = "") -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT id, file_name, created_at FROM analyses WHERE owner = ? AND file_name LIKE ? "
                "ORDER BY id DESC",
                (owner, f"%{search}%"),
            ).fetchall()
        return [{"id": r[0], "file_name": r[1], "created_at": r[2]} for r in rows]

    def get(self, owner: str, analysis_id: int) -> tuple[dict[str, Any], bytes | None] | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT data_json, pdf FROM analyses WHERE owner = ? AND id = ?", (owner, analysis_id)
            ).fetchone()
        return (json.loads(row[0]), row[1]) if row else None

    def clear(self, owner: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM analyses WHERE owner = ?", (owner,))
