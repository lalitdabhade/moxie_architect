"""Server-rendered admin pages. They are thin shells; data changes go through /api/admin."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pymysql.connections import Connection

from app.db import get_db
from app.security import load_session, new_login_csrf_token, set_login_csrf_cookie
from app.templating import templates

router = APIRouter(prefix="/admin", include_in_schema=False)


def _render(request: Request, template: str, session: dict, active: str, **context):
    response = templates.TemplateResponse(
        request, template,
        {"admin": {"username": session["username"]}, "csrf_token": session["csrf_token"],
         "active": active, **context},
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def _login_redirect() -> RedirectResponse:
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/login")
def login_page(request: Request, conn: Connection = Depends(get_db)):
    if load_session(conn, request):
        return RedirectResponse("/admin", status_code=303)
    token = new_login_csrf_token()
    response = templates.TemplateResponse(request, "admin/login.html", {"login_csrf": token})
    set_login_csrf_cookie(response, token)
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("")
def dashboard(request: Request, conn: Connection = Depends(get_db)):
    session = load_session(conn, request)
    if not session:
        return _login_redirect()
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM projects")
        project_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM inquiries")
        inquiry_count = cur.fetchone()["n"]
    return _render(request, "admin/dashboard.html", session, "dashboard",
                   project_count=project_count, inquiry_count=inquiry_count)
