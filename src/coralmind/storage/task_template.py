import json
import sqlite3
from typing import Any

from .connection import get_connection

__all__ = ["TaskTemplateRO", "TaskTemplateStorage"]


class TaskTemplateRO:
    """TaskTemplate database record object"""

    def __init__(self, id: int, task_template_json: str, total_length: int):
        self.id = id
        self.task_template_json = task_template_json
        self.total_length = total_length

    @property
    def material_names(self) -> list[str]:
        data: dict[str, Any] = json.loads(self.task_template_json)
        return list(data.get("material_names", []))

    @property
    def requirements(self) -> str:
        data: dict[str, Any] = json.loads(self.task_template_json)
        return str(data.get("requirements", ""))


class TaskTemplateStorage:
    """TaskTemplate persistent storage - stateless design"""

    @staticmethod
    def init_table() -> None:
        """Initialize database table"""
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_template (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_template_json TEXT NOT NULL UNIQUE,
                    total_length INTEGER NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_template_length ON task_template(total_length)
            """)
            conn.commit()

    @staticmethod
    def insert(task_template_json: str) -> int:
        """Insert new record, return existing ID if already exists"""
        total_length = len(task_template_json)

        with get_connection() as conn:
            try:
                cursor = conn.execute(
                    "INSERT INTO task_template (task_template_json, total_length) VALUES (?, ?)",
                    (task_template_json, total_length)
                )
                conn.commit()
                return cursor.lastrowid or 0
            except sqlite3.IntegrityError:
                cursor = conn.execute(
                    "SELECT id FROM task_template WHERE task_template_json = ?",
                    (task_template_json,)
                )
                row = cursor.fetchone()
                return int(row["id"])

    @staticmethod
    def find_by_content(task_template_json: str) -> TaskTemplateRO | None:
        """Find task template by content"""
        total_length = len(task_template_json)

        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, task_template_json, total_length FROM task_template WHERE total_length = ?",
                (total_length,)
            )
            rows = cursor.fetchall()

            for row in rows:
                if row["task_template_json"] == task_template_json:
                    return TaskTemplateRO(
                        id=row["id"],
                        task_template_json=row["task_template_json"],
                        total_length=row["total_length"]
                    )

            return None

    @staticmethod
    def get_by_id(task_template_id: int) -> TaskTemplateRO | None:
        """Get task template by ID"""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, task_template_json, total_length FROM task_template WHERE id = ?",
                (task_template_id,)
            )
            row = cursor.fetchone()
            if row:
                return TaskTemplateRO(
                    id=row["id"],
                    task_template_json=row["task_template_json"],
                    total_length=row["total_length"]
                )
            return None
