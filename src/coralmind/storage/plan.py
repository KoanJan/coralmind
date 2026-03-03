from .connection import get_connection

__all__ = ["PlanRO", "PlanStorage"]


class PlanRO:
    """Plan database record object"""

    def __init__(self, id: int, task_template_id: int, plan_json: str, exec_times: int, total_score: int):
        self.id = id
        self.task_template_id = task_template_id
        self.plan_json = plan_json
        self.exec_times = exec_times
        self.total_score = total_score

    @property
    def avg_score(self) -> float:
        if self.exec_times == 0:
            return 0.0
        return self.total_score / self.exec_times


class PlanStorage:
    """Plan persistent storage - stateless design"""

    @staticmethod
    def init_table() -> None:
        """Initialize database table"""
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_model (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_template_id INTEGER NOT NULL,
                    plan_json TEXT NOT NULL UNIQUE,
                    exec_times INTEGER NOT NULL DEFAULT 0,
                    total_score INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_plan_task_template ON plan_model(task_template_id)
            """)
            conn.commit()

    @staticmethod
    def insert(task_template_id: int, plan_json: str, first_score: int) -> int:
        """Insert new record"""
        with get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO plan_model (task_template_id, plan_json, exec_times, total_score) VALUES (?, ?, 1, ?)",
                (task_template_id, plan_json, first_score)
            )
            conn.commit()
            return cursor.lastrowid or 0

    @staticmethod
    def upsert(task_template_id: int, plan_json: str, first_score: int) -> None:
        """Insert or update record"""
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO plan_model (task_template_id, plan_json, exec_times, total_score) VALUES (?, ?, 1, ?) "
                "ON CONFLICT(plan_json) DO UPDATE SET total_score = total_score + ?, exec_times = exec_times + 1",
                (task_template_id, plan_json, first_score, first_score)
            )
            conn.commit()

    @staticmethod
    def get_by_task_template_id(task_template_id: int) -> list[PlanRO]:
        """Get all plans by task template ID"""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, task_template_id, plan_json, exec_times, total_score FROM plan_model WHERE task_template_id = ?",
                (task_template_id,)
            )
            rows = cursor.fetchall()
            return [
                PlanRO(
                    id=row["id"],
                    task_template_id=row["task_template_id"],
                    plan_json=row["plan_json"],
                    exec_times=row["exec_times"],
                    total_score=row["total_score"]
                )
                for row in rows
            ]

    @staticmethod
    def update_score(plan_id: int, score: int) -> None:
        """Update plan score"""
        with get_connection() as conn:
            conn.execute(
                "UPDATE plan_model SET total_score = total_score + ?, exec_times = exec_times + 1 WHERE id = ?",
                (score, plan_id)
            )
            conn.commit()

    @staticmethod
    def get_by_id(plan_id: int) -> PlanRO | None:
        """Get plan by ID"""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, task_template_id, plan_json, exec_times, total_score FROM plan_model WHERE id = ?",
                (plan_id,)
            )
            row = cursor.fetchone()
            if row:
                return PlanRO(
                    id=row["id"],
                    task_template_id=row["task_template_id"],
                    plan_json=row["plan_json"],
                    exec_times=row["exec_times"],
                    total_score=row["total_score"]
                )
            return None
