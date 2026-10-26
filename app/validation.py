"""Input validation shared by API endpoints. Each helper returns (value, error_message)."""
import re

from app.constants import (
    AREA_MAX_SQFT, AREA_MIN_SQFT, BUDGET_RANGES, HOUSE_TYPES, SECTIONS_BY_ID, SECTIONS_BY_SLUG,
    SERVICE_TYPES, TITLE_MAX_LENGTH,
)

_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
MOBILE_RE = re.compile(r"^\d{10}$")
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
                      r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*\.[A-Za-z]{2,}$")


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


def clean_mobile(value: str | None) -> tuple[str | None, str | None]:
    digits = re.sub(r"[\s-]", "", value or "")
    if not digits:
        return None, "Mobile number is required."
    if not MOBILE_RE.match(digits):
        return None, "Enter a valid 10-digit mobile number."
    return digits, None


def clean_email(value: str | None) -> tuple[str | None, str | None]:
    email = (value or "").strip()
    if not email:
        return None, "Email is required."
    if len(email) > 254 or not EMAIL_RE.match(email):
        return None, "Enter a valid email address."
    local, _, domain = email.rpartition("@")
    return f"{local}@{domain.lower()}", None


def _choice(value: str | None, choices: dict, required_msg: str) -> tuple[str | None, str | None]:
    value = (value or "").strip()
    if not value:
        return None, required_msg
    if value not in choices:
        return None, "Choose one of the listed options."
    return value, None


def clean_area(value: str | None) -> tuple[int | None, str | None]:
    raw = (value or "").strip().replace(",", "")
    if not raw:
        return None, "Area is required."
    if not raw.isdigit():
        return None, "Enter the area as a whole number of square feet."
    area = int(raw)
    if not AREA_MIN_SQFT <= area <= AREA_MAX_SQFT:
        return None, f"Area must be between {AREA_MIN_SQFT:,} and {AREA_MAX_SQFT:,} sq ft."
    return area, None


def validate_inquiry(form: dict[str, str | None], has_layout: bool) -> tuple[dict, dict[str, str]]:
    """Validate an inquiry. Only the chosen service type's fields are read; the rest are ignored.

    Returns (clean_values, field_errors). The layout file itself is validated separately on save.
    """
    errors: dict[str, str] = {}
    data: dict = {"house_type": None, "house_type_other": None, "area_sqft": None}

    def take(field, result):
        value, error = result
        if error:
            errors[field] = error
        data[field] = value

    take("name", clean_text(form.get("name"), "Name", 2, 100))
    take("mobile", clean_mobile(form.get("mobile")))
    take("email", clean_email(form.get("email")))
    take("address", clean_text(form.get("address"), "Address", 5, 500))
    take("service_type", _choice(form.get("service_type"), SERVICE_TYPES, "Choose the service you need."))
    take("budget_range", _choice(form.get("budget_range"), BUDGET_RANGES, "Choose a budget range."))

    if data["service_type"] == "interior":
        take("house_type", _choice(form.get("house_type"), HOUSE_TYPES, "Choose a house type."))
        if data["house_type"] == "other":
            take("house_type_other", clean_text(form.get("house_type_other"), "House type", 2, 100))
    elif data["service_type"] == "bungalow_apartment":
        take("area_sqft", clean_area(form.get("area_sqft")))
        if not has_layout:
            errors["layout"] = "Upload your layout (JPG, PNG or PDF)."
    return data, errors
