"""Turn DB rows into the JSON shapes returned by the API (shared by public + admin)."""
from app.constants import BUDGET_RANGES, HOUSE_TYPES, SECTIONS_BY_ID, SERVICE_TYPES


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


def _option(value: str | None, labels: dict) -> dict | None:
    return {"value": value, "label": labels[value]} if value else None


def inquiry_json(row: dict) -> dict:
    """Full inquiry for admins. The layout is exposed only as a protected download URL."""
    house_label = None
    if row["house_type"] == "other":
        house_label = f"Other: {row['house_type_other']}"
    elif row["house_type"]:
        house_label = HOUSE_TYPES[row["house_type"]]
    return {
        "id": row["id"],
        "name": row["name"],
        "mobile": row["mobile"],
        "email": row["email"],
        "address": row["address"],
        "service_type": _option(row["service_type"], SERVICE_TYPES),
        "house_type": _option(row["house_type"], HOUSE_TYPES),
        "house_type_other": row["house_type_other"],
        "house_type_label": house_label,
        "area_sqft": row["area_sqft"],
        "budget_range": _option(row["budget_range"], BUDGET_RANGES),
        "layout": ({"filename": row["layout_original_name"],
                    "download_url": f"/api/admin/inquiries/{row['id']}/layout"}
                   if row["layout_file_path"] else None),
        "created_at": row["created_at"].isoformat(),
    }
