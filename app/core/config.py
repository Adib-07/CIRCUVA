import os

class Settings:
    PROJECT_NAME: str = "Circuva"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cva_super_secret_production_key_2026_circuva")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./circuva.db")

    # Uploads
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

    # Centralized Photography Registry (real, locally-stored royalty-free photography)
    DEMO_PHOTOGRAPHY = {
        "hero_campus": "/static/assets/images/hero-campus-1.jpg",
        "campus_aerial": "/static/assets/images/campus-aerial-1.jpg",
        "campus_building": "/static/assets/images/hero-campus-1.jpg",
        "waste_bins": "/static/assets/images/cat-broken-1.jpg",
        "recycling_station": "/static/assets/images/cat-recycling-1.jpg",
        "overflowing_bin": "/static/assets/images/cat-waste-1.jpg",
        "litter_outdoor": "/static/assets/images/cat-litter-1.jpg",
        "illegal_dumping": "/static/assets/images/cat-illegal-1.jpg",
        "plastic_waste": "/static/assets/images/cat-plastic-1.jpg",
        "food_waste": "/static/assets/images/cat-food-1.jpg",
        "e_waste": "/static/assets/images/cat-ewaste-1.jpg",
        "cleaning_worker": "/static/assets/images/cat-waste-2.jpg",
        "before_dirty": "/static/assets/images/before-waste-1.jpg",
        "after_clean": "/static/assets/images/after-clean-1.jpg"
    }

settings = Settings()

# Persona definitions used by demo mode, seeding, and the /auth/personas endpoint.
# Emails are realistic SAMPLE demo accounts only — no real credentials are ever hardcoded.
PERSONAS = [
    {
        "role": "student",
        "label": "Student",
        "email": "alex.student@greenfield.edu",
        "description": "Report issues, track resolutions, and earn impact.",
        "capabilities": ["Submit waste reports", "Upload photos", "Track status", "View personal impact"],
    },
    {
        "role": "faculty",
        "label": "Faculty / Staff",
        "email": "priya.faculty@greenfield.edu",
        "description": "Submit and monitor reports, see nearby issues and campus info.",
        "capabilities": ["Submit reports", "Monitor campus reports", "View nearby issues", "Campus information"],
    },
    {
        "role": "facilities",
        "label": "Facilities / Waste Ops",
        "email": "marcus.worker@greenfield.edu",
        "description": "Triage incoming reports, prioritize, and close out tasks.",
        "capabilities": ["View incoming reports", "Prioritize & assign", "Update status", "Hotspot & metrics"],
    },
    {
        "role": "admin",
        "label": "Sustainability Admin",
        "email": "sarah.admin@greenfield.edu",
        "description": "Campus-wide analytics, trends, impact, and resolution performance.",
        "capabilities": ["Campus analytics", "Trends & impact", "Hotspots", "Resolution performance"],
    },
]

# Canonical issue types surfaced in the report form, filters, seed data, and analytics.
ISSUE_TYPES = [
    "Overflowing Bin",
    "Recycling Contamination",
    "Illegal Dumping",
    "Litter Hotspot",
    "Damaged Waste Infrastructure",
    "Missed Collection",
    "Other",
]

# Ordered report status lifecycle with display labels used by steppers and filters.
STATUS_LIFECYCLE = [
    {"key": "submitted", "label": "Reported"},
    {"key": "acknowledged", "label": "Acknowledged"},
    {"key": "assigned", "label": "Assigned"},
    {"key": "in_progress", "label": "In Progress"},
    {"key": "resolved", "label": "Resolved"},
    {"key": "verified", "label": "Verified"},
]

# Urgency is surfaced in the report form and filters (stored as `severity`).
URGENCY_LEVELS = ["low", "medium", "high", "critical"]
