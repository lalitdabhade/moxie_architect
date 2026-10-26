"""Fixed reference data shared by the API, templates and validation."""

SECTIONS = [
    {
        "id": 1,
        "slug": "residential-interior",
        "key": "residential",  # short prefix for uploaded image filenames
        "name": "Residential Interior Design",
        "tagline": "Homes shaped around the way you live.",
    },
    {
        "id": 2,
        "slug": "commercial-interior",
        "key": "commercial",
        "name": "Commercial Interior Design",
        "tagline": "Workplaces and retail spaces with purpose.",
    },
    {
        "id": 3,
        "slug": "bungalow-design",
        "key": "bungalow",
        "name": "Bungalow Design",
        "tagline": "Independent homes, designed from the ground up.",
    },
    {
        "id": 4,
        "slug": "apartment-commercial-complex",
        "key": "complex",
        "name": "Apartment and Commercial Complex",
        "tagline": "Residential and commercial buildings at scale.",
    },
]

SECTIONS_BY_ID = {s["id"]: s for s in SECTIONS}
SECTIONS_BY_SLUG = {s["slug"]: s for s in SECTIONS}

PROJECT_IMAGE_TYPES = {"jpeg", "png", "webp"}
PROJECT_IMAGE_MAX_BYTES = 5 * 1024 * 1024
MAX_IMAGES_PER_UPLOAD = 30
TITLE_MAX_LENGTH = 200

LAYOUT_FILE_TYPES = {"jpeg", "png", "pdf"}
LAYOUT_MAX_BYTES = 10 * 1024 * 1024
AREA_MIN_SQFT = 50
AREA_MAX_SQFT = 1_000_000
INQUIRIES_PER_PAGE = 25

SERVICE_TYPES = {
    "interior": "Interior",
    "bungalow_apartment": "Bungalow/Apartment Design",
}

HOUSE_TYPES = {
    "1bhk": "1 BHK",
    "2bhk": "2 BHK",
    "3bhk": "3 BHK",
    "bungalow": "Bungalow",
    "other": "Other",
}

BUDGET_RANGES = {
    "under_5l": "Under 5L",
    "5_10l": "5-10L",
    "10_20l": "10-20L",
    "20_50l": "20-50L",
    "above_50l": "Above 50L",
}
