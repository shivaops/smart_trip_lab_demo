"""
repo/greeting_repo.py
---------------------
DB lookup for greeting_mst.

Design:
- greeting_key is generated in MySQL from greeting_msg.
- Python only normalizes the user input the same way and searches exact key.
- If a greeting row is found, reply comes from DB.
- If no row is found, caller continues existing Smart Trip flow.
"""

from typing import Optional, Dict, Any
import re

from db.session import get_conn


def normalize_greeting_key(message: str | None) -> str:
    """
    Normalize user greeting text exactly like greeting_mst.greeting_key.

    Rule locked for Smart Trip:
    - remove spaces
    - remove special characters
    - keep alphabets A-Z only
    - compare ignoring case

    Examples:
      "Hi!!!"              -> "hi"
      "H I"                -> "hi"
      "As-Salaam-Alaikum"  -> "assalaamalaikum"
    """
    if not message:
        return ""
    return re.sub(r"[^A-Za-z]", "", str(message)).lower()


def _build_greeting_user_message(row: Dict[str, Any]) -> str:
    """
    Build final assistant message from prefix + reply + suffix.
    Empty/null parts are ignored.
    """
    parts: list[str] = []
    for col in ("prefix_msg", "reply_msg", "suffix_msg"):
        value = (row.get(col) or "").strip()
        if value:
            parts.append(value)
    return "\n\n".join(parts)


def find_active_greeting_by_message(message: str | None) -> Optional[Dict[str, Any]]:
    """
    Finds one active greeting row by normalized user message.

    Returns:
      None when not matched.
      Dict with greeting details and user_message when matched.
    """
    greeting_key = normalize_greeting_key(message)
    if not greeting_key:
        return None

    sql = """
        SELECT
            greeting_id,
            greeting_type,
            greeting_msg,
            greeting_key,
            reply_msg,
            prefix_msg,
            suffix_msg,
            lang_code
        FROM greeting_mst
        WHERE greeting_key = %s
          AND is_active = 1
        LIMIT 1
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (greeting_key,))
            row = cur.fetchone()

    if not row:
        return None

    row["user_message"] = _build_greeting_user_message(row)
    row["input_greeting_key"] = greeting_key
    return row
