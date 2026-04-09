from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List


class AttendanceDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_name TEXT NOT NULL,
                    recognized_at TEXT NOT NULL,
                    liveness_score REAL NOT NULL,
                    UNIQUE(person_name, date(recognized_at))
                )
                """
            )

    def mark_attendance(self, person_name: str, liveness_score: float) -> bool:
        """Return True if newly inserted, False when already marked today."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO attendance (person_name, recognized_at, liveness_score)
                VALUES (?, ?, ?)
                """,
                (person_name, timestamp, liveness_score),
            )
            return cursor.rowcount > 0

    def fetch_recent(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, person_name, recognized_at, liveness_score
                FROM attendance
                ORDER BY recognized_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def daily_counts(self) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT date(recognized_at) AS day, COUNT(*) AS count
                FROM attendance
                GROUP BY day
                ORDER BY day ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def rows_as_csv(self) -> str:
        rows = self.fetch_recent(limit=10000)
        header = "id,person_name,recognized_at,liveness_score"
        body = [
            f"{r['id']},{r['person_name']},{r['recognized_at']},{r['liveness_score']:.3f}"
            for r in rows
        ]
        return "\n".join([header] + body)

    def rows_as_iter(self) -> Iterable[Dict[str, Any]]:
        return self.fetch_recent(limit=10000)
