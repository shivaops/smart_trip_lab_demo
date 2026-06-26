"""
core/session.py
---------------
Session cookie signing + verification.

Why:
- We store session_uuid in a browser cookie.
- But cookie can be modified by user.
- So we SIGN it using itsdangerous.
- On every request, we UNSIGN it to verify integrity.
"""

import os
from dotenv import load_dotenv
from itsdangerous import URLSafeSerializer, BadSignature

load_dotenv()


def _serializer() -> URLSafeSerializer:
    """
    Creates a serializer object using SESSION_SECRET.

    If SESSION_SECRET changes, old cookies become invalid (expected behavior).
    """
    secret = os.getenv("SESSION_SECRET", "change_me")
    return URLSafeSerializer(secret_key=secret, salt="tt_agentic_session")


def sign_session_uuid(session_uuid: str) -> str:
    """
    Converts a plain session_uuid into a signed token to store in cookie.
    """
    s = _serializer()
    return s.dumps({"session_uuid": session_uuid})


def unsign_session_token(token: str) -> str | None:
    """
    Converts signed cookie token back to session_uuid.

    Returns:
      session_uuid (str) if valid, else None.
    """
    s = _serializer()
    try:
        data = s.loads(token)
        return data.get("session_uuid")
    except BadSignature:
        return None
