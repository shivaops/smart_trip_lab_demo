"""
repo/session_repo.py
--------------------
DB queries related to chat_session.
"""

from typing import Optional, Dict, Any
import uuid

from db.session import get_conn

def get_active_session_by_uuid(session_uuid: str) -> Optional[Dict[str, Any]]:
    """
    Returns ACTIVE session row by session_uuid, or None.
    """
    sql = """
        SELECT session_id, session_uuid, user_id, app_code, interaction_mode, status, started_at, ended_at
        FROM chat_session
        WHERE session_uuid = %s
          AND status = 'ACTIVE'
        LIMIT 1
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_uuid,))
            return cur.fetchone()
            
def create_chat_session(user_id: int, interaction_mode: str = "GUI") -> Dict[str, Any]:
    """
    Inserts a new chat_session row and returns identifiers.

    interaction_mode:
      - "GUI" or "LLM" (locked design)

    Returns:
      {"session_id": ..., "session_uuid": "..."}
    """
    session_uuid = str(uuid.uuid4())

    sql = """
        INSERT INTO chat_session (session_uuid, user_id, app_code, interaction_mode, status)
        VALUES (%s, %s, 'ARS', %s, 'ACTIVE')
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_uuid, user_id, interaction_mode))
            session_id = cur.lastrowid

    return {"session_id": session_id, "session_uuid": session_uuid}

"""
repo/session_repo.py
--------------------
Add session close support.

Repo rule:
- SQL only
- no FastAPI, no cookies, no Jinja
"""

from typing import Optional
from db.session import get_conn


def close_chat_session_by_uuid(session_uuid: str) -> int:
    """
    Mark a session CLOSED in DB using session_uuid.

    Returns:
      number of rows updated (0 or 1)

    Why uuid:
    - We store session_uuid in cookie (signed)
    - We can safely look up and close the exact session
    """
    sql = """
        UPDATE chat_session
        SET status = 'CLOSED',
            ended_at = NOW()
        WHERE session_uuid = %s
          AND status = 'ACTIVE'
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (session_uuid,))
            return cur.rowcount
