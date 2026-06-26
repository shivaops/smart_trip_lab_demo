"""
scripts/set_password.py
-----------------------
Admin utility to set/reset password_hash in DB.

How to run:
  cd C:\smart_trip_lab\smart_trip
  .venv\Scripts\activate
  python scripts\set_password.py shiva MyNewPassword123

What it does:
- finds user by username
- hashes password using bcrypt
- stores hash in app_user.password_hash 
"""

import sys
from pathlib import Path

# Add project root (C:\tt_agentic) to Python import path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repo.user_repo import get_user_by_username, update_user_password_hash
from core.passwords import hash_password


def main():
    if len(sys.argv) != 3:
        print("Usage: python scripts\\set_password.py <username> <new_password>")
        sys.exit(1)

    username = sys.argv[1].strip()
    new_password = sys.argv[2]

    user = get_user_by_username(username)
    if not user:
        print(f"User not found: {username}")
        sys.exit(2)

    new_hash = hash_password(new_password)
    update_user_password_hash(int(user["user_id"]), new_hash)

    print(f"Password updated successfully for user: {username}")


if __name__ == "__main__":
    main()
