"""Server-rendered public pages."""
from fastapi import APIRouter, Request

from app.templating import templates

router = APIRouter(include_in_schema=False)


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "public/home.html", {"active": "home"})
