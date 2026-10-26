"""Server-rendered public pages."""
from fastapi import APIRouter, Depends, Request
from pymysql.connections import Connection

from app.constants import (
    AREA_MAX_SQFT, AREA_MIN_SQFT, BUDGET_RANGES, HOUSE_TYPES, LAYOUT_MAX_BYTES, SECTIONS, SERVICE_TYPES,
)
from app.db import get_db
from app.repositories import projects as projects_repo
from app.serializers import project_json
from app.templating import templates

router = APIRouter(include_in_schema=False)


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "public/home.html", {"active": "home"})


@router.get("/inquiry")
def inquiry(request: Request):
    return templates.TemplateResponse(request, "public/inquiry.html", {
        "active": "inquiry",
        "service_types": SERVICE_TYPES,
        "house_types": HOUSE_TYPES,
        "budget_ranges": BUDGET_RANGES,
        "area_min": AREA_MIN_SQFT,
        "area_max": AREA_MAX_SQFT,
        "layout_max_bytes": LAYOUT_MAX_BYTES,
    })


def _section_page(section: dict):
    def page(request: Request, conn: Connection = Depends(get_db)):
        projects = projects_repo.list_public_projects(conn, section["id"])
        return templates.TemplateResponse(request, "public/section.html", {
            "active": section["slug"],
            "section": section,
            "section_number": SECTIONS.index(section) + 1,
            "projects": [project_json(p) for p in projects],
        })
    return page


# One explicit route per section (no catch-all), e.g. /residential-interior
for _section in SECTIONS:
    router.add_api_route(f"/{_section['slug']}", _section_page(_section), methods=["GET"],
                         name=f"section-{_section['slug']}")
