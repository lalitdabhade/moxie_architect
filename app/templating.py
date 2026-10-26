from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.constants import SECTIONS

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))
templates.env.globals["SECTIONS"] = SECTIONS
# Placeholder branding - change here once the firm's name is final.
templates.env.globals["SITE"] = {
    "name": "Moxie",
    "subtitle": "Architect",
    "full_name": "Moxie Architect",
    "location": "Pune, Maharashtra",
}
