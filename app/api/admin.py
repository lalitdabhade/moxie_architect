"""Admin JSON API: /api/admin/*"""
from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from pydantic import BaseModel, Field
from pymysql.connections import Connection

from app.config import settings
from app.constants import (
    MAX_IMAGES_PER_UPLOAD, PROJECT_IMAGE_MAX_BYTES, PROJECT_IMAGE_TYPES, SECTIONS_BY_ID,
)
from app.db import get_db
from app.errors import ApiError
from app.repositories import admins as admins_repo
from app.repositories import projects as projects_repo
from app.security import (
    LOGIN_CSRF_COOKIE, burn_password_check, check_login_csrf, end_session,
    login_limiter, require_admin, start_session, verify_password,
)
from app.serializers import project_json
from app.uploads import delete_file, is_present, save_upload, slugify
from app.validation import clean_title, parse_section

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


# ---------- projects ----------

class ProjectPatchIn(BaseModel):
    title: str | None = None
    section_id: int | None = None


class ImageOrderIn(BaseModel):
    image_ids: list[int] = Field(min_length=1, max_length=500)


def _present_files(images: list[UploadFile]) -> list[UploadFile]:
    files = [f for f in images if is_present(f)]
    if len(files) > MAX_IMAGES_PER_UPLOAD:
        raise ApiError(422, f"Upload at most {MAX_IMAGES_PER_UPLOAD} images at a time.",
                       fields={"images": f"At most {MAX_IMAGES_PER_UPLOAD} images per upload."})
    return files


def _store_images(conn: Connection, project_id: int, section_id: int, title: str,
                  files: list[UploadFile], saved: list[str]) -> None:
    """Save files to disk and insert rows. Appends each stored filename to `saved` for cleanup."""
    stem = f"{SECTIONS_BY_ID[section_id]['key']}-{slugify(title, 50)}-{project_id}"
    order = projects_repo.next_sort_order(conn, project_id)
    for upload in files:
        filename = save_upload(upload, settings.project_upload_dir, PROJECT_IMAGE_TYPES,
                               PROJECT_IMAGE_MAX_BYTES, stem, field="images")
        saved.append(filename)
        projects_repo.add_image(conn, project_id, filename, order)
        order += 1


def _rollback_files(conn: Connection, saved: list[str]) -> None:
    conn.rollback()
    for filename in saved:
        delete_file(settings.project_upload_dir, filename)


def _get_project_or_404(conn: Connection, project_id: int, for_update: bool = False) -> dict:
    project = projects_repo.get_project(conn, project_id, for_update=for_update)
    if project is None:
        raise ApiError(404, "Project not found.")
    return project


@router.get("/projects")
def list_projects(section: str | None = None, session: dict = Depends(require_admin),
                  conn: Connection = Depends(get_db)):
    section_id = None
    if section:
        section_id, error = parse_section(section)
        if error:
            raise ApiError(422, error, fields={"section": error})
    return {"projects": [project_json(p) for p in projects_repo.list_projects(conn, section_id)]}


@router.post("/projects", status_code=201)
def create_project(section_id: str = Form(""), title: str = Form(""),
                   images: list[UploadFile] = File(default=[]),
                   session: dict = Depends(require_admin), conn: Connection = Depends(get_db)):
    errors = {}
    section, err = parse_section(section_id)
    if err:
        errors["section_id"] = err
    clean, err = clean_title(title)
    if err:
        errors["title"] = err
    files = _present_files(images)
    if not files:
        errors["images"] = "Add at least one image."
    if errors:
        raise ApiError(422, "Please correct the highlighted fields.", fields=errors)

    saved: list[str] = []
    try:
        project_id = projects_repo.create_project(conn, section, clean)
        _store_images(conn, project_id, section, clean, files, saved)
        conn.commit()
    except Exception:
        _rollback_files(conn, saved)
        raise
    return {"project": project_json(projects_repo.get_project(conn, project_id))}


@router.get("/projects/{project_id}")
def get_project(project_id: int, session: dict = Depends(require_admin), conn: Connection = Depends(get_db)):
    return {"project": project_json(_get_project_or_404(conn, project_id))}


@router.patch("/projects/{project_id}")
def update_project(project_id: int, body: ProjectPatchIn, session: dict = Depends(require_admin),
                   conn: Connection = Depends(get_db)):
    project = _get_project_or_404(conn, project_id)
    errors = {}
    title, section = project["title"], project["section_id"]
    if body.title is not None:
        title, err = clean_title(body.title)
        if err:
            errors["title"] = err
    if body.section_id is not None:
        section, err = parse_section(body.section_id)
        if err:
            errors["section_id"] = err
    if errors:
        raise ApiError(422, "Please correct the highlighted fields.", fields=errors)
    projects_repo.update_project(conn, project_id, section, title)
    conn.commit()
    return {"project": project_json(projects_repo.get_project(conn, project_id))}


@router.delete("/projects/{project_id}")
def delete_project(project_id: int, session: dict = Depends(require_admin), conn: Connection = Depends(get_db)):
    _get_project_or_404(conn, project_id)
    paths = projects_repo.delete_project(conn, project_id)
    conn.commit()
    for filename in paths:
        delete_file(settings.project_upload_dir, filename)
    return {"ok": True}


@router.post("/projects/{project_id}/images", status_code=201)
def add_images(project_id: int, images: list[UploadFile] = File(default=[]),
               session: dict = Depends(require_admin), conn: Connection = Depends(get_db)):
    project = _get_project_or_404(conn, project_id, for_update=True)
    files = _present_files(images)
    if not files:
        raise ApiError(422, "Choose at least one image.", fields={"images": "Choose at least one image."})
    saved: list[str] = []
    try:
        _store_images(conn, project_id, project["section_id"], project["title"], files, saved)
        conn.commit()
    except Exception:
        _rollback_files(conn, saved)
        raise
    return {"project": project_json(projects_repo.get_project(conn, project_id))}


@router.delete("/projects/{project_id}/images/{image_id}")
def delete_image(project_id: int, image_id: int, session: dict = Depends(require_admin),
                 conn: Connection = Depends(get_db)):
    _get_project_or_404(conn, project_id)
    path = projects_repo.delete_image(conn, project_id, image_id)
    if path is None:
        raise ApiError(404, "Image not found.")
    conn.commit()
    delete_file(settings.project_upload_dir, path)
    return {"project": project_json(projects_repo.get_project(conn, project_id))}


@router.put("/projects/{project_id}/images/order")
def reorder_images(project_id: int, body: ImageOrderIn, session: dict = Depends(require_admin),
                   conn: Connection = Depends(get_db)):
    _get_project_or_404(conn, project_id, for_update=True)
    if not projects_repo.reorder_images(conn, project_id, body.image_ids):
        conn.rollback()
        raise ApiError(422, "The image list is out of date. Reload the page and try again.",
                       fields={"image_ids": "Must contain each of the project's images exactly once."})
    conn.commit()
    return {"project": project_json(projects_repo.get_project(conn, project_id))}
