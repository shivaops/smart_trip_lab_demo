"""
db/session.py
-------------
DB connection helper (PyMySQL).

FastAPI concept:
- Routes should NOT create raw DB connections everywhere.
- We keep DB connection code in one place.
- Repo functions call `get_conn()` and run SQL.

We use DictCursor so rows come as:
  {"user_id": 1, "username": "shiva", ...}
instead of tuples.
"""

import os
from contextlib import contextmanager

import pymysql
from dotenv import load_dotenv

load_dotenv()  # reads .env into environment variables


def _db_config() -> dict:
    """
    Reads DB settings from .env.

    You can change .env without touching Python files.
    """
    return {
        "host": os.getenv("TT_DB_HOST", "127.0.0.1"),
        "port": int(os.getenv("TT_DB_PORT", "3306")),
        "user": os.getenv("TT_DB_USER", "root"),
        "password": os.getenv("TT_DB_PASSWORD", ""),
        "database": os.getenv("TT_DB_NAME", "tt_agentic"),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }


@contextmanager
def get_conn():
    """
    Context manager that safely opens and closes DB connection.

    Usage:
      with get_conn() as conn:
          ... use conn ...

    Why:
    - Ensures connection closes even if errors happen.
    """
    cfg = _db_config()
    conn = pymysql.connect(**cfg)

    try:
        yield conn
    finally:
        conn.close()
