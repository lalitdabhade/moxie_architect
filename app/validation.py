"""Input validation shared by API endpoints. Each helper returns (value, error_message)."""
import re

from app.constants import SECTIONS_BY_ID, SECTIONS_BY_SLUG, TITLE_MAX_LENGTH

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(value: str | None, field_label: str, min_length: int, max_length: int) -> tuple[str | None, str | None]:
    text = re.sub(r"\s+", " ", (value or "")).strip()
    if not text:
        return None, f"{field_label} is required."
    if _CONTROL_CHARS.search(text):
        return None, f"{field_label} contains invalid characters."
    if len(text) < min_length:
        return None, f"{field_label} must be at least {min_length} characters."
    if len(text) > max_length:
        return None, f"{field_label} must be at most {max_length} characters."
    return text, None


def clean_title(value: str | None) -> tuple[str | None, str | None]:
    return clean_text(value, "Title", 2, TITLE_MAX_LENGTH)


def parse_section(value: str | int | None) -> tuple[int | None, str | None]:
    """Accepts a section id (1-4) or slug."""
    if value is None or str(value).strip() == "":
        return None, "Choose a section."
    raw = str(value).strip()
    if raw.isdigit() and int(raw) in SECTIONS_BY_ID:
        return int(raw), None
    if raw in SECTIONS_BY_SLUG:
        return SECTIONS_BY_SLUG[raw]["id"], None
    return None, "Choose a valid section."
