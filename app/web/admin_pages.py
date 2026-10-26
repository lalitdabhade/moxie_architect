"""Server-rendered admin pages. They are thin shells; data changes go through /api/admin."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pymysql.connections import Connection
from starlette.exceptions import HTTPException

from app.api.admin import inquiry_page
from app.constants import (
    MAX_IMAGES_PER_UPLOAD, PROJECT_IMAGE_MAX_BYTES, SECTIONS, SECTIONS_BY_SLUG, SERVICE_TYPES,
    TITLE_MAX_LENGTH,
)
from app.db import get_db
from app.repositories import inquiries as inquiries_repo
from app.repositories import projects as projects_repo
from app.security import load_session, new_login_csrf_token, set_login_csrf_cookie
from app.serializers import inquiry_json, project_json
from app.templating import templates

router = APIRouter(prefix="/admin", include_in_schema=False)

UPLOAD_LIMITS = {
    "max_bytes": PROJECT_IMAGE_MAX_BYTES,
    "max_files": MAX_IMAGES_PER_UPLOAD,
    "title_max": TITLE_MAX_LENGTH,
}


class LoginRequired(Exception):
    pass


def admin_session(request: Request, conn: Connection = Depends(get_db)) -> dict:
    session = load_session(conn, request)
    if session is None:
        raise LoginRequired()
    return session


def login_required_handler(request: Request, exc: LoginRequired):
    return RedirectResponse("/admin/login", status_code=303)


def _render(request: Request, template: str, session: dict, active: str, **context):
    response = templates.TemplateResponse(
        request, template,
        {"admin": {"username": session["username"]}, "csrf_token": session["csrf_token"],
         "active": active, **context},
    )
    response.headers["Cache-Control"] = "no-store"
    return response


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
def dashboard(request: Request, session: dict = Depends(admin_session), conn: Connection = Depends(get_db)):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM projects")
        project_count = cur.fetchone()["n"]
        cur.execute("SELECT COUNT(*) AS n FROM inquiries")
        inquiry_count = cur.fetchone()["n"]
    recent = [inquiry_json(r) for r in inquiries_repo.list_page(conn, None, 5, 0)]
    return _render(request, "admin/dashboard.html", session, "dashboard",
                   project_count=project_count, inquiry_count=inquiry_count, recent_inquiries=recent)


@router.get("/projects")
def projects_page(request: Request, section: str | None = None,
                  session: dict = Depends(admin_session), conn: Connection = Depends(get_db)):
    current = SECTIONS_BY_SLUG.get(section or "")
    projects = projects_repo.list_projects(conn, current["id"] if current else None)
    return _render(request, "admin/projects_list.html", session, "projects",
                   projects=[project_json(p) for p in projects],
                   counts=projects_repo.count_by_section(conn),
                   current_section=current)


@router.get("/projects/new")
def new_project_page(request: Request, section: str | None = None, session: dict = Depends(admin_session)):
    preselect = SECTIONS_BY_SLUG.get(section or "")
    return _render(request, "admin/project_new.html", session, "projects",
                   preselect_id=preselect["id"] if preselect else None,
                   limits=UPLOAD_LIMITS, sections=SECTIONS)


@router.get("/projects/{project_id}")
def edit_project_page(request: Request, project_id: int,
                      session: dict = Depends(admin_session), conn: Connection = Depends(get_db)):
    project = projects_repo.get_project(conn, project_id)
    if project is None:
        raise HTTPException(404, "Project not found.")
    return _render(request, "admin/project_edit.html", session, "projects",
                   project=project_json(project), limits=UPLOAD_LIMITS, sections=SECTIONS)


@router.get("/inquiries")
def inquiries_page(request: Request, service_type: str | None = None, page: int = 1,
                   session: dict = Depends(admin_session), conn: Connection = Depends(get_db)):
    current = service_type if service_type in SERVICE_TYPES else None
    data = inquiry_page(conn, current, page)
    return _render(request, "admin/inquiries_list.html", session, "inquiries",
                   current_service=current, service_types=SERVICE_TYPES, **data)


@router.get("/inquiries/{inquiry_id}")
def inquiry_detail_page(request: Request, inquiry_id: int,
                        session: dict = Depends(admin_session), conn: Connection = Depends(get_db)):
    row = inquiries_repo.get(conn, inquiry_id)
    if row is None:
        raise HTTPException(404, "Inquiry not found.")
    return _render(request, "admin/inquiry_detail.html", session, "inquiries", inquiry=inquiry_json(row))
