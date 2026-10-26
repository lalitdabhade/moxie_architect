"""Turn DB rows into the JSON shapes returned by the API (shared by public + admin)."""
from app.constants import SECTIONS_BY_ID


def section_json(section_id: int) -> dict:
    s = SECTIONS_BY_ID[section_id]
    return {"id": s["id"], "slug": s["slug"], "name": s["name"]}


def image_url(path: str) -> str:
    return f"/uploads/projects/{path}"


def project_json(project: dict) -> dict:
    return {
        "id": project["id"],
        "title": project["title"],
        "section": section_json(project["section_id"]),
        "created_at": project["created_at"].isoformat(),
        "images": [
            {"id": img["id"], "url": image_url(img["path"]), "sort_order": img["sort_order"]}
            for img in project.get("images", [])
        ],
    }
