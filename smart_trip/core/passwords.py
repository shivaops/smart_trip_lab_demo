"""
core/passwords.py
-----------------
Password hashing + verification helpers.

Why this file exists:
- Routers should NOT contain hashing logic.
- Repo should NOT contain hashing logic.
- Core layer holds reusable business utilities.

Industry rule:
- Store only hashed password in DB.
- Never store plain password.
"""

from passlib.context import CryptContext

# bcrypt is a strong password hashing algorithm.
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """
    Input:
      plain_password: user typed password (plain text)

    Output:
      bcrypt hash string, safe to store in DB.
    """
    return _pwd.hash(plain_password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Returns True if the plain password matches stored hash.
    """
    if not stored_hash:
        return False
    return _pwd.verify(plain_password, stored_hash)
