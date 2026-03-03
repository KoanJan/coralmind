"""Database Connection Management - Simplified Version"""
import atexit
import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "coralmind.db"

_db_path: str = DEFAULT_DB_PATH
_db_path_lock = threading.Lock()

_atexit_registered = False
_atexit_lock = threading.Lock()


def set_db_path(path: str | Path) -> None:
    """Set database path (must be called before first connection use)"""
    global _db_path
    with _db_path_lock:
        _db_path = str(path)


def get_db_path() -> str:
    """Get current database path"""
    with _db_path_lock:
        return _db_path


@contextmanager
def get_connection() -> Any:
    """Get database connection context manager

    Usage example:
        with get_connection() as conn:
            cursor = conn.execute("SELECT * FROM table")
            rows = cursor.fetchall()
    """
    db_path = get_db_path()
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise
    finally:
        if conn:
            conn.close()


def _cleanup_at_exit() -> None:
    """Cleanup on program exit (sqlite3 connections are auto-closed)"""
    pass


def _register_atexit() -> None:
    """Register atexit cleanup function (thread-safe, only once)"""
    global _atexit_registered
    with _atexit_lock:
        if not _atexit_registered:
            atexit.register(_cleanup_at_exit)
            _atexit_registered = True


_register_atexit()
