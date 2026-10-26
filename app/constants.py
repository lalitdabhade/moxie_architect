"""Fixed reference data shared by the API, templates and validation."""

SECTIONS = [
    {
        "id": 1,
        "slug": "residential-interior",
        "name": "Residential Interior Design",
        "tagline": "Homes shaped around the way you live.",
    },
    {
        "id": 2,
        "slug": "commercial-interior",
        "name": "Commercial Interior Design",
        "tagline": "Workplaces and retail spaces with purpose.",
    },
    {
        "id": 3,
        "slug": "bungalow-design",
        "name": "Bungalow Design",
        "tagline": "Independent homes, designed from the ground up.",
    },
    {
        "id": 4,
        "slug": "apartment-commercial-complex",
        "name": "Apartment and Commercial Complex",
        "tagline": "Residential and commercial buildings at scale.",
    },
]

SECTIONS_BY_ID = {s["id"]: s for s in SECTIONS}
SECTIONS_BY_SLUG = {s["slug"]: s for s in SECTIONS}

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
