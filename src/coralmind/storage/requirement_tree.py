from ..model.requirement_tree import RequirementTree
from .connection import get_connection

__all__ = ["RequirementTreeRO", "RequirementTreeStorage"]


class RequirementTreeRO:
    """RequirementTree database record object"""

    def __init__(self, id: int, task_template_id: int, tree_json: str):
        self.id = id
        self.task_template_id = task_template_id
        self.tree_json = tree_json

    def to_tree(self) -> RequirementTree:
        """Convert database record to RequirementTree object"""
        return RequirementTree.model_validate_json(self.tree_json)


class RequirementTreeStorage:
    """RequirementTree persistent storage - stateless design"""

    @staticmethod
    def init_table() -> None:
        """Initialize database table"""
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS requirement_tree (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_template_id INTEGER NOT NULL UNIQUE,
                    tree_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_requirement_tree_template ON requirement_tree(task_template_id)
            """)
            conn.commit()

    @staticmethod
    def upsert(task_template_id: int, tree: RequirementTree) -> int:
        """Insert or update requirement tree for a task template"""
        tree_json = tree.model_dump_json()

        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id FROM requirement_tree WHERE task_template_id = ?",
                (task_template_id,)
            )
            existing = cursor.fetchone()

            if existing:
                conn.execute(
                    "UPDATE requirement_tree SET tree_json = ? WHERE task_template_id = ?",
                    (tree_json, task_template_id)
                )
                conn.commit()
                return int(existing["id"])
            else:
                cursor = conn.execute(
                    "INSERT INTO requirement_tree (task_template_id, tree_json) VALUES (?, ?)",
                    (task_template_id, tree_json)
                )
                conn.commit()
                return cursor.lastrowid or 0

    @staticmethod
    def get_by_task_template_id(task_template_id: int) -> RequirementTreeRO | None:
        """Get requirement tree by task template ID"""
        with get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, task_template_id, tree_json FROM requirement_tree WHERE task_template_id = ?",
                (task_template_id,)
            )
            row = cursor.fetchone()
            if row:
                return RequirementTreeRO(
                    id=row["id"],
                    task_template_id=row["task_template_id"],
                    tree_json=row["tree_json"]
                )
            return None
