from datetime import datetime

from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.constants import SECTIONS

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def display_datetime(value: str | datetime, with_time: bool = True) -> str:
    """'2026-10-26T14:05:00' -> '26 Oct 2026, 14:05'"""
    dt = datetime.fromisoformat(value) if isinstance(value, str) else value
    return dt.strftime("%d %b %Y, %H:%M" if with_time else "%d %b %Y")


templates.env.filters["datetime"] = display_datetime
templates.env.globals["SECTIONS"] = SECTIONS
# Placeholder branding - change here once the firm's name is final.
templates.env.globals["SITE"] = {
    "name": "Moxie",
    "subtitle": "Architect",
    "full_name": "Moxie Architect",
    "location": "Pune, Maharashtra",
}
