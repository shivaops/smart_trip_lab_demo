"""
repo/user_repo.py
-----------------
DB queries related to app_user table only.

Rule:
- Repo layer = SQL only
- No FastAPI code here
- No HTML/Jinja code here
"""

from typing import Optional, Dict, Any

from db.session import get_conn


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Fetch one user row by username.

    Returns:
      dict like:
        {
          "user_id": 1,
          "username": "shiva",
          "first_name": "Shiva",
          "last_name": "Naik",
          "password_hash": "",
          "is_active": 1
        }
      OR None if not found.
    """
    sql = """
        SELECT
          user_id,
          username,         
          password_hash,
          is_active
        FROM app_user
        WHERE username = %s
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (username,))
            return cur.fetchone()

def update_user_password_hash(user_id: int, password_hash: str) -> None:
    """
    Updates app_user.password_hash for a given user_id.
    Used for admin reset scripts (or future UI change password).

    Repo rule:
    - Only SQL here
    - No hashing here (hashing is done in core/passwords.py)
    """
    sql = """
        UPDATE app_user
        SET password_hash = %s
        WHERE user_id = %s
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (password_hash, user_id))

def get_user_by_id(user_id: int):
    """
    Fetch one user row by user_id.
    """
    sql = """
        SELECT user_id, username, is_active
        FROM app_user
        WHERE user_id = %s
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (user_id,))
            return cur.fetchone()

