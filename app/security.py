"""Password hashing, server-side sessions, CSRF and login rate limiting."""
import hashlib
import hmac
import secrets
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, Request, Response
from pymysql.connections import Connection

from app.config import settings
from app.db import get_db
from app.errors import ApiError
from app.repositories import sessions as sessions_repo

SESSION_COOKIE = "admin_session"
LOGIN_CSRF_COOKIE = "login_csrf"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
BCRYPT_MAX_BYTES = 72


# ---------- passwords ----------

def hash_password(password: str) -> str:
    raw = password.encode("utf-8")
    if len(raw) > BCRYPT_MAX_BYTES:
        raise ValueError("Password must be at most 72 bytes.")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
    except ValueError:
        return False


# Used when the username does not exist, so the response time does not reveal it.
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt(rounds=12)).decode("ascii")


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


# ---------- sessions ----------

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def start_session(conn: Connection, response: Response, admin_id: int) -> str:
    """Create a session, set the cookie, return the session's CSRF token."""
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_hex(32)
    now = _utcnow()
    sessions_repo.create(conn, _hash_token(token), admin_id, csrf_token,
                         now, now + timedelta(hours=settings.session_hours))
    response.set_cookie(
        SESSION_COOKIE, token,
        max_age=settings.session_hours * 3600,
        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/",
    )
    return csrf_token


def end_session(conn: Connection, request: Request, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        sessions_repo.delete(conn, _hash_token(token))
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True,
                           secure=settings.cookie_secure, samesite="lax")


def load_session(conn: Connection, request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token or len(token) > 128:
        return None
    return sessions_repo.get_valid(conn, _hash_token(token), _utcnow())


def check_csrf(request: Request, expected: str) -> None:
    sent = request.headers.get(CSRF_HEADER, "")
    if not sent or not hmac.compare_digest(sent, expected):
        raise ApiError(403, "Invalid or missing CSRF token.", code="csrf_failed")


def require_admin(request: Request, conn: Connection = Depends(get_db)) -> dict:
    """API dependency: valid session required; CSRF header required on unsafe methods."""
    session = load_session(conn, request)
    if session is None:
        raise ApiError(401, "Please log in.")
    if request.method not in SAFE_METHODS:
        check_csrf(request, session["csrf_token"])
    return session


# ---------- login-form CSRF (no session exists yet) ----------
# Double-submit cookie, HMAC-signed with SESSION_SECRET so it cannot be forged.

def _sign(value: str) -> str:
    return hmac.new(settings.session_secret.encode(), value.encode(), hashlib.sha256).hexdigest()


def new_login_csrf_token() -> str:
    return secrets.token_hex(32)


def set_login_csrf_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        LOGIN_CSRF_COOKIE, f"{token}.{_sign(token)}",
        max_age=3600, httponly=True, secure=settings.cookie_secure, samesite="strict", path="/",
    )


def check_login_csrf(request: Request) -> None:
    cookie = request.cookies.get(LOGIN_CSRF_COOKIE, "")
    token, _, signature = cookie.partition(".")
    sent = request.headers.get(CSRF_HEADER, "")
    if not (token and signature and sent
            and hmac.compare_digest(signature, _sign(token))
            and hmac.compare_digest(sent, token)):
        raise ApiError(403, "Your login form expired. Please reload the page.", code="csrf_failed")


# ---------- login rate limiting ----------

class LoginRateLimiter:
    """In-memory sliding window of failed logins (resets when the server restarts)."""

    def __init__(self, max_per_user: int = 5, max_per_ip: int = 20, window_seconds: int = 15 * 60):
        self.max_per_user = max_per_user
        self.max_per_ip = max_per_ip
        self.window = window_seconds
        self._failures: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str, now: float) -> deque[float]:
        q = self._failures.setdefault(key, deque())
        while q and q[0] <= now - self.window:
            q.popleft()
        return q

    def retry_after(self, ip: str, username: str) -> int:
        """Seconds until another attempt is allowed, or 0 if allowed now."""
        now = time.monotonic()
        with self._lock:
            waits = []
            for key, limit in ((f"u:{ip}:{username}", self.max_per_user), (f"ip:{ip}", self.max_per_ip)):
                q = self._recent(key, now)
                if len(q) >= limit:
                    waits.append(int(q[0] + self.window - now) + 1)
            return max(waits, default=0)

    def record_failure(self, ip: str, username: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._recent(f"u:{ip}:{username}", now).append(now)
            self._recent(f"ip:{ip}", now).append(now)

    def reset(self, ip: str, username: str) -> None:
        with self._lock:
            self._failures.pop(f"u:{ip}:{username}", None)

    def clear(self) -> None:
        with self._lock:
            self._failures.clear()


login_limiter = LoginRateLimiter()


class RateLimiter:
    """Simple in-memory sliding window: at most `limit` hits per key per window."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> int:
        """Record a hit. Returns 0 if allowed, otherwise seconds to wait (the hit is not recorded)."""
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= now - self.window:
                q.popleft()
            if len(q) >= self.limit:
                return int(q[0] + self.window - now) + 1
            q.append(now)
            return 0

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


inquiry_limiter = RateLimiter(limit=10, window_seconds=60 * 60)
