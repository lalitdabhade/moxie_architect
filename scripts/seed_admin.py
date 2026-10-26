"""Create (or reset the password of) the admin user from ADMIN_USERNAME / ADMIN_PASSWORD in .env.

Usage:  python -m scripts.seed_admin
"""
import re
import sys

from app import db
from app.config import settings
from app.repositories import admins as admins_repo
from app.security import BCRYPT_MAX_BYTES, hash_password

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.@+-]{3,50}$")  # plain names or email addresses
MIN_PASSWORD_LENGTH = 8


def main() -> int:
    username = settings.admin_username.strip()
    password = settings.admin_password
    if not USERNAME_RE.match(username):
        print("ADMIN_USERNAME must be 3-50 characters: letters, digits, _ . @ + -", file=sys.stderr)
        return 1
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"ADMIN_PASSWORD must be at least {MIN_PASSWORD_LENGTH} characters.", file=sys.stderr)
        return 1
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        print(f"ADMIN_PASSWORD must be at most {BCRYPT_MAX_BYTES} bytes.", file=sys.stderr)
        return 1

    db.ensure_database()
    db.init_schema()
    conn = db.connect()
    try:
        result = admins_repo.upsert(conn, username, hash_password(password))
    finally:
        conn.close()
    print(f"Admin '{username}' {result}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
