"""Public JSON API (no login): /api/*"""
import os
import uuid

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pymysql.connections import Connection

from app.config import settings
from app.constants import (
    AREA_MAX_SQFT, AREA_MIN_SQFT, BUDGET_RANGES, HOUSE_TYPES, LAYOUT_FILE_TYPES, LAYOUT_MAX_BYTES,
    SECTIONS, SECTIONS_BY_SLUG, SERVICE_TYPES,
)
from app.db import get_db
from app.errors import ApiError
from app.repositories import inquiries as inquiries_repo
from app.repositories import projects as projects_repo
from app.security import inquiry_limiter
from app.serializers import project_json
from app.uploads import delete_file, is_present, save_upload
from app.validation import validate_inquiry

THANK_YOU = "Thank you! We have received your inquiry and will contact you soon."

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/sections")
def list_sections(conn: Connection = Depends(get_db)):
    counts = projects_repo.count_public_by_section(conn)
    return {"sections": [
        {"id": s["id"], "slug": s["slug"], "name": s["name"], "tagline": s["tagline"],
         "project_count": counts.get(s["id"], 0)}
        for s in SECTIONS
    ]}


@router.get("/sections/{slug}/projects")
def section_projects(slug: str, conn: Connection = Depends(get_db)):
    section = SECTIONS_BY_SLUG.get(slug)
    if section is None:
        raise ApiError(404, "Section not found.")
    projects = projects_repo.list_public_projects(conn, section["id"])
    return {
        "section": {"id": section["id"], "slug": section["slug"], "name": section["name"]},
        "projects": [project_json(p) for p in projects],
    }


@router.get("/projects/{project_id}")
def get_project(project_id: int, conn: Connection = Depends(get_db)):
    project = projects_repo.get_project(conn, project_id)
    if project is None or not project["images"]:
        raise ApiError(404, "Project not found.")
    return {"project": project_json(project)}


def _options(labels: dict) -> list[dict]:
    return [{"value": k, "label": v} for k, v in labels.items()]


@router.get("/inquiry-options")
def inquiry_options():
    """Choices for the inquiry form (lets the mobile app build the same form)."""
    return {
        "service_types": _options(SERVICE_TYPES),
        "house_types": _options(HOUSE_TYPES),
        "budget_ranges": _options(BUDGET_RANGES),
        "area_sqft": {"min": AREA_MIN_SQFT, "max": AREA_MAX_SQFT},
        "layout": {"types": ["jpg", "jpeg", "png", "pdf"], "max_bytes": LAYOUT_MAX_BYTES},
    }


def _safe_original_name(filename: str) -> str:
    name = os.path.basename(filename.replace("\\", "/")).strip()
    name = "".join(ch for ch in name if ch.isprintable() and ch not in '"<>|:*?')
    return name[-150:] or "layout"


@router.post("/inquiries", status_code=201)
def create_inquiry(
    request: Request,
    name: str = Form(""), mobile: str = Form(""), email: str = Form(""), address: str = Form(""),
    service_type: str = Form(""), house_type: str = Form(""), house_type_other: str = Form(""),
    area_sqft: str = Form(""), budget_range: str = Form(""),
    website: str = Form(""),  # honeypot: hidden from people, bots tend to fill it
    layout: UploadFile | None = File(None),
    conn: Connection = Depends(get_db),
):
    if website:
        return {"inquiry": None, "message": THANK_YOU}

    form = {"name": name, "mobile": mobile, "email": email, "address": address,
            "service_type": service_type, "house_type": house_type, "house_type_other": house_type_other,
            "area_sqft": area_sqft, "budget_range": budget_range}
    data, errors = validate_inquiry(form, has_layout=is_present(layout))
    if errors:
        raise ApiError(422, "Please correct the highlighted fields.", fields=errors)

    ip = request.client.host if request.client else "unknown"
    wait = inquiry_limiter.hit(ip)
    if wait:
        raise ApiError(429, "Too many inquiries from your connection. Please try again later.",
                       headers={"Retry-After": str(wait)})

    stored = None
    try:
        # Only the bungalow/apartment branch accepts a layout; a stray file on interior is ignored.
        if data["service_type"] == "bungalow_apartment":
            stored = save_upload(layout, settings.layout_upload_dir, LAYOUT_FILE_TYPES, LAYOUT_MAX_BYTES,
                                 uuid.uuid4().hex, field="layout")
            data["layout_file_path"] = stored
            data["layout_original_name"] = _safe_original_name(layout.filename)
        inquiry_id = inquiries_repo.create(conn, data)
        conn.commit()
    except Exception:
        conn.rollback()
        if stored:
            delete_file(settings.layout_upload_dir, stored)
        raise
    row = inquiries_repo.get(conn, inquiry_id)
    return {"inquiry": {"id": inquiry_id, "created_at": row["created_at"].isoformat()}, "message": THANK_YOU}
