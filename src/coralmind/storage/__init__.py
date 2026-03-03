from .connection import (
    DEFAULT_DB_PATH,
    get_connection,
    get_db_path,
    set_db_path,
)
from .plan import PlanRO, PlanStorage
from .task_template import TaskTemplateRO, TaskTemplateStorage

_initialized = False


def init_storage() -> None:
    """Initialize all storage tables (idempotent, can be called multiple times)"""
    global _initialized
    if not _initialized:
        TaskTemplateStorage.init_table()
        PlanStorage.init_table()
        _initialized = True


__all__ = [
    "get_connection",
    "set_db_path",
    "get_db_path",
    "DEFAULT_DB_PATH",
    "PlanRO",
    "PlanStorage",
    "TaskTemplateRO",
    "TaskTemplateStorage",
    "init_storage",
]
