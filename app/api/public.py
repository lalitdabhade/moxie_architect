"""Public JSON API (no login): /api/*"""
from fastapi import APIRouter, Depends
from pymysql.connections import Connection

from app.constants import SECTIONS, SECTIONS_BY_SLUG
from app.db import get_db
from app.errors import ApiError
from app.repositories import projects as projects_repo
from app.serializers import project_json

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
