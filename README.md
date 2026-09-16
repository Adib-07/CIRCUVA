# Circuva

> See it. Report it. Resolve it.

A full-stack web application for campus environmental issue reporting and resolution tracking. Built with FastAPI, SQLAlchemy, and vanilla JavaScript.

---

## Problem

Campus environments face recurring waste management issues — overflowing bins, illegal dumping, recycling contamination, and missed collections. Existing reporting processes are fragmented (email, paper forms, informal requests), making it difficult to track resolution status, identify hotspots, or measure response performance.

## Solution

Circuva provides a closed-loop workflow: **report → dispatch → resolve → verify**. Students and staff submit issues with photos and location data. Facility operations teams receive assignments, perform cleanup, and upload proof. Administrators monitor analytics and operational hotspots through role-based dashboards.

---

## Key Capabilities

- **Issue Reporting Wizard** — Multi-step form for submitting environmental issues with category, location, severity, and photo evidence
- **Interactive SVG Campus Map** — Custom-built pseudo-3D campus visualization with severity-coded incident markers and building details
- **Role-Based Dashboards** — Separate views for students (report tracking), facility workers (task management), and administrators (analytics)
- **Analytics Dashboard** — Custom SVG charts showing category distribution, location hotspots, severity trends, and resolution metrics
- **Before/After Comparison** — Visual slider component for cleanup verification
- **Verification Loop** — Reporters confirm resolution status, with auto-reopen for rejected verifications
- **Notification Backend** — Automated notification creation for assignments, resolutions, and status events (database layer; no frontend inbox UI yet)
- **Impact Scoring** — Gamified contributor tracking for student reporters

---

## How It Works

1. A reporter submits an issue through the 5-step wizard (category → building/GPS → severity → photo upload → summary)
2. The system generates a unique report code (`CVA-2026-XXXXXX`)
3. An admin assigns the report to a facility worker
4. The worker resolves the issue and uploads an after-photo
5. The original reporter verifies whether the problem was fixed
6. Analytics update in real-time across all dashboards

---

## Architecture

```
CIRCUVA/
├── app/
│   ├── api/              # FastAPI routers (auth, reports, analytics)
│   ├── auth/             # JWT authentication and RBAC
│   ├── core/             # Application configuration
│   ├── database/         # SQLAlchemy session and seed data
│   ├── models/           # Database models (User, Campus, Report, etc.)
│   ├── schemas/          # Pydantic request/response schemas
│   └── main.py           # FastAPI application entrypoint
├── static/
│   ├── css/styles.css    # Application styles
│   ├── js/               # Frontend JavaScript modules
│   │   ├── app.js        # Main application controller
│   │   ├── campusmap.js  # Custom SVG campus map
│   │   ├── charts.js     # Custom SVG chart engine
│   │   └── campus-twin.js
│   ├── img/              # SVG illustrations
│   └── assets/images/    # Photography assets
├── templates/
│   └── index.html        # Single-page application template
├── tests/
│   └── test_api.py       # API endpoint tests
├── uploads/              # User-uploaded evidence images (runtime)
├── .env.example          # Environment configuration template
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.10+) |
| ORM | SQLAlchemy 2.x |
| Database | SQLite |
| Authentication | JWT (python-jose) with role-based access control |
| Password Hashing | PBKDF2-SHA256 |
| Image Processing | Pillow |
| Templating | Jinja2 |
| Frontend | Vanilla HTML5 / CSS3 / JavaScript (no frameworks) |
| Charts | Custom SVG rendering engine (no external library) |
| Campus Map | Custom SVG pseudo-3D visualization (no external library) |

---

## Setup

### Prerequisites

- Python 3.10+

### Installation

```bash
# Clone the repository
git clone https://github.com/Adib-07/CIRCUVA.git
cd CIRCUVA

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Configuration

```bash
# Copy the example environment file
cp .env.example .env

# For local development, generate a JWT secret key:
python -c "import secrets; print(secrets.token_hex(32))"

# Add the generated key to your .env file:
# SECRET_KEY=<your-generated-key>
```

### Seed Database & Run

```bash
# Seed demo data (Greenfield University campus)
python -m app.database.seed

# Start the development server
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 in your browser.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (required for production) | Random per-process (dev only) |
| `DATABASE_URL` | Database connection string | `sqlite:///./circuva.db` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:8000` |

---

## Demo Accounts

Use the 1-Click Login toolbar in the application interface.

These are **demo accounts** for the seeded Greenfield University campus. All passwords are `Password123!`.

| Role | Name | Email |
|------|------|-------|
| Student Reporter | Alex Rivera | `alex.student@greenfield.edu` |
| Facility Operations Worker | Marcus Vance | `marcus.worker@greenfield.edu` |
| Campus Administrator | Dr. Sarah Jenkins | `sarah.admin@greenfield.edu` |

---

## Testing

```bash
# Run the test suite
python -m pytest tests/ -v

# Verify application imports
python -c "from app.main import app; print('OK')"
```

---

## Current Status

This is a functional prototype / portfolio demonstration. The application is fully operational for local development with seeded demo data.

**Implemented:**
- Complete issue reporting workflow with photo uploads
- Role-based authentication and authorization
- Interactive SVG campus map and analytics charts
- Reporter verification loop with auto-reopen
- Notification backend (database layer, no frontend UI)

**Known Limitations:**
- SQLite database (not suitable for production concurrency)
- File-based uploads (no cloud storage integration)
- Fixed password salt shared across all users (acceptable for demo; production should use per-user salts)
- CORS defaults to localhost only
- No email/notification delivery integration
- No automated deployment pipeline

---

## License

This project is for demonstration purposes.
