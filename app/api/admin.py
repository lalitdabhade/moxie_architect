"""Admin JSON API: /api/admin/*"""
from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from pymysql.connections import Connection

from app.db import get_db
from app.errors import ApiError
from app.repositories import admins as admins_repo
from app.security import (
    LOGIN_CSRF_COOKIE, burn_password_check, check_login_csrf, end_session,
    login_limiter, require_admin, start_session, verify_password,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, conn: Connection = Depends(get_db)):
    check_login_csrf(request)
    ip = _client_ip(request)
    username = body.username.strip()
    key_user = username.lower()

    wait = login_limiter.retry_after(ip, key_user)
    if wait:
        raise ApiError(429, f"Too many failed attempts. Try again in {max(1, wait // 60)} minute(s).",
                       headers={"Retry-After": str(wait)})

    admin = admins_repo.get_by_username(conn, username)
    if admin is None:
        burn_password_check(body.password)
        ok = False
    else:
        ok = verify_password(body.password, admin["password_hash"])
    if not ok:
        login_limiter.record_failure(ip, key_user)
        raise ApiError(401, "Invalid username or password.", code="invalid_credentials")

    login_limiter.reset(ip, key_user)
    csrf_token = start_session(conn, response, admin["id"])
    response.delete_cookie(LOGIN_CSRF_COOKIE, path="/")
    return {"admin": {"id": admin["id"], "username": admin["username"]}, "csrf_token": csrf_token}


@router.post("/logout")
def logout(request: Request, response: Response, session: dict = Depends(require_admin),
           conn: Connection = Depends(get_db)):
    end_session(conn, request, response)
    return {"ok": True}


@router.get("/me")
def me(session: dict = Depends(require_admin)):
    return {"admin": {"id": session["admin_id"], "username": session["username"]},
            "csrf_token": session["csrf_token"]}
