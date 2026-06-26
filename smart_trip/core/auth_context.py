"""
core/auth_context.py
--------------------
Helper functions to get:
- session_uuid from signed cookie
- session row from DB
- current user from DB

Routers will call these helpers so code stays clean.
"""

import os
from dotenv import load_dotenv

from core.session import unsign_session_token
from repo.session_repo import get_active_session_by_uuid
from repo.user_repo import get_user_by_id

load_dotenv()
COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "tt_session")


def get_session_uuid_from_request(request) -> str | None:
    """
    Reads signed cookie token and unsigns it.

    Returns:
      session_uuid (str) if valid else None
    """
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return unsign_session_token(token)


def get_current_user(request):
    """
    Returns current logged-in user dict or None.

    Flow:
    - cookie -> session_uuid 
    - session_uuid -> active chat_session row
    - session.user_id -> app_user row
    """
    session_uuid = get_session_uuid_from_request(request)
    if not session_uuid:
        return None

    sess = get_active_session_by_uuid(session_uuid)
    if not sess:
        return None

    user = get_user_by_id(int(sess["user_id"]))
    return user
