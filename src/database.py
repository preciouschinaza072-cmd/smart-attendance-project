from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np


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
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin', 'lecturer', 'student'))
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS courses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    lecturer_id INTEGER NOT NULL,
                    FOREIGN KEY(lecturer_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS enrollments (
                    student_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    PRIMARY KEY(student_id, course_id),
                    FOREIGN KEY(student_id) REFERENCES users(id),
                    FOREIGN KEY(course_id) REFERENCES courses(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    user_id INTEGER PRIMARY KEY,
                    embedding BLOB NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    course_id INTEGER NOT NULL,
                    recognized_at TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    liveness_score REAL NOT NULL,
                    FOREIGN KEY(student_id) REFERENCES users(id),
                    FOREIGN KEY(course_id) REFERENCES courses(id),
                    UNIQUE(student_id, course_id, date(recognized_at))
                )
                """
            )

    def seed_demo_data(self) -> None:
        with self.connect() as conn:
            has_users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            if has_users:
                return
            conn.execute("INSERT INTO users(name, role) VALUES ('Admin One', 'admin')")
            conn.execute("INSERT INTO users(name, role) VALUES ('Lecturer One', 'lecturer')")
            conn.execute("INSERT INTO users(name, role) VALUES ('Student One', 'student')")
            conn.execute("INSERT INTO courses(name, lecturer_id) VALUES ('Computer Vision', 2)")
            conn.execute("INSERT INTO enrollments(student_id, course_id) VALUES (3, 1)")

    def create_user(self, name: str, role: str) -> int:
        with self.connect() as conn:
            cur = conn.execute("INSERT INTO users(name, role) VALUES (?, ?)", (name, role))
            return int(cur.lastrowid)

    def list_users(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            if role:
                rows = conn.execute("SELECT id, name, role FROM users WHERE role = ? ORDER BY id", (role,)).fetchall()
            else:
                rows = conn.execute("SELECT id, name, role FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def create_course(self, name: str, lecturer_id: int) -> int:
        with self.connect() as conn:
            cur = conn.execute("INSERT INTO courses(name, lecturer_id) VALUES (?, ?)", (name, lecturer_id))
            return int(cur.lastrowid)

    def list_courses(self, lecturer_id: Optional[int] = None) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            if lecturer_id:
                rows = conn.execute(
                    """
                    SELECT c.id, c.name, c.lecturer_id, u.name AS lecturer_name
                    FROM courses c
                    JOIN users u ON u.id = c.lecturer_id
                    WHERE c.lecturer_id = ?
                    ORDER BY c.id
                    """,
                    (lecturer_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT c.id, c.name, c.lecturer_id, u.name AS lecturer_name
                    FROM courses c
                    JOIN users u ON u.id = c.lecturer_id
                    ORDER BY c.id
                    """
                ).fetchall()
        return [dict(r) for r in rows]

    def enroll_student(self, student_id: int, course_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO enrollments(student_id, course_id) VALUES (?, ?)",
                (student_id, course_id),
            )

    def is_enrolled(self, student_id: int, course_id: int) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM enrollments WHERE student_id = ? AND course_id = ?",
                (student_id, course_id),
            ).fetchone()
            return row is not None

    def save_embedding(self, user_id: int, embedding: np.ndarray) -> None:
        blob = np.asarray(embedding, dtype=np.float32).tobytes()
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO face_embeddings(user_id, embedding, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET embedding=excluded.embedding, updated_at=excluded.updated_at
                """,
                (user_id, blob, ts),
            )

    def get_embedding(self, user_id: int) -> Optional[np.ndarray]:
        with self.connect() as conn:
            row = conn.execute("SELECT embedding FROM face_embeddings WHERE user_id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return np.frombuffer(row["embedding"], dtype=np.float32)

    def get_course_student_embeddings(self, course_id: int) -> List[Dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT u.id AS student_id, u.name AS student_name, f.embedding
                FROM enrollments e
                JOIN users u ON u.id = e.student_id
                JOIN face_embeddings f ON f.user_id = u.id
                WHERE e.course_id = ? AND u.role = 'student'
                """,
                (course_id,),
            ).fetchall()
        output = []
        for row in rows:
            output.append(
                {
                    "student_id": row["student_id"],
                    "student_name": row["student_name"],
                    "embedding": np.frombuffer(row["embedding"], dtype=np.float32),
                }
            )
        return output

    def mark_attendance(self, student_id: int, course_id: int, confidence: float, liveness_score: float) -> bool:
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with self.connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO attendance(student_id, course_id, recognized_at, confidence, liveness_score)
                VALUES (?, ?, ?, ?, ?)
                """,
                (student_id, course_id, ts, confidence, liveness_score),
            )
            return cur.rowcount > 0

    def fetch_attendance(self, course_id: Optional[int] = None, lecturer_id: Optional[int] = None, limit: int = 200):
        query = """
        SELECT a.id, a.student_id, s.name AS student_name, a.course_id, c.name AS course_name,
               a.recognized_at, a.confidence, a.liveness_score
        FROM attendance a
        JOIN users s ON s.id = a.student_id
        JOIN courses c ON c.id = a.course_id
        """
        conditions = []
        params: List[Any] = []

        if course_id:
            conditions.append("a.course_id = ?")
            params.append(course_id)
        if lecturer_id:
            conditions.append("c.lecturer_id = ?")
            params.append(lecturer_id)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY a.recognized_at DESC LIMIT ?"
        params.append(limit)

        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def daily_counts(self, course_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = "SELECT date(recognized_at) AS day, COUNT(*) AS count FROM attendance"
        params: List[Any] = []
        if course_id:
            query += " WHERE course_id = ?"
            params.append(course_id)
        query += " GROUP BY day ORDER BY day"
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [dict(r) for r in rows]

    def rows_as_csv(self, course_id: Optional[int] = None) -> str:
        rows = self.fetch_attendance(course_id=course_id, limit=10000)
        header = "id,student_id,student_name,course_id,course_name,recognized_at,confidence,liveness_score"
        body = [
            f"{r['id']},{r['student_id']},{r['student_name']},{r['course_id']},{r['course_name']},"
            f"{r['recognized_at']},{r['confidence']:.4f},{r['liveness_score']:.4f}"
            for r in rows
        ]
        return "\n".join([header] + body)

    def rows_as_iter(self, course_id: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        return self.fetch_attendance(course_id=course_id, limit=10000)
