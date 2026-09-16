# CIRCUVA

> See it. Report it. Resolve it.

A campus environmental issue reporting and operations platform with role-based workflows, incident tracking, verification, and operational analytics.

---

## Problem

Campus environments face recurring waste management issues — overflowing bins, illegal dumping, recycling contamination, and missed collections. Existing reporting processes are fragmented (email, paper forms, informal requests), making it difficult to track resolution status, identify hotspots, or measure response performance.

## Solution

CIRCUVA provides a closed-loop workflow: **report → dispatch → resolve → verify**. Students and staff submit issues with photos and location data. Facility operations teams receive assignments, perform cleanup, and upload proof. Administrators monitor analytics and operational hotspots through role-based dashboards.

---

## Core Workflow

1. A reporter submits an issue through the 5-step wizard (category → building/GPS → severity → photo upload → summary)
2. The system generates a unique report code (`CVA-2026-XXXXXX`)
3. An admin acknowledges and assigns the report to a facility worker
4. The worker resolves the issue and uploads an after-photo
5. The original reporter verifies whether the problem was fixed
6. Analytics update in real-time across all dashboards

---

## Key Capabilities

- **Issue Reporting Wizard** — Multi-step form for submitting environmental issues with category, location, severity, and photo evidence
- **Interactive SVG Campus Map** — Custom-built pseudo-3D campus visualization with severity-coded incident markers
- **Role-Based Dashboards** — Separate views for students (report tracking), facility workers (task management), and administrators (analytics)
- **Analytics Dashboard** — Custom SVG charts showing category distribution, location hotspots, severity trends, and resolution metrics
- **Before/After Comparison** — Visual slider component for cleanup verification
- **Verification Loop** — Reporters confirm resolution status, with auto-reopen for rejected verifications
- **Notification Backend** — Automated notification creation for assignments, resolutions, and status events
- **Impact Scoring** — Gamified contributor tracking for student reporters

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
│   ├── conftest.py       # Test fixtures and helpers
│   └── test_api.py       # Comprehensive API tests
├── uploads/              # User-uploaded evidence images (runtime)
├── .env.example          # Environment configuration template
├── requirements.txt      # Python dependencies
└── README.md
```

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.10+) |
| ORM | SQLAlchemy 2.x |
| Database | SQLite (development) |
| Authentication | JWT (python-jose) with role-based access control |
| Password Hashing | PBKDF2-SHA256 |
| Templating | Jinja2 |
| Frontend | Vanilla HTML5 / CSS3 / JavaScript (no frameworks) |
| Charts | Custom SVG rendering engine (no external library) |
| Campus Map | Custom SVG pseudo-3D visualization (no external library) |

---

## Security Model

### Role-Based Access Control

| Role | Permissions |
|------|-------------|
| **Student** | Create reports, view own reports, verify own resolved reports, view own profile |
| **Faculty** | Create reports, monitor campus reports, view nearby issues |
| **Facilities** | Acknowledge reports, assign tasks, update status, resolve issues, view hotspots |
| **Admin** | Full campus administration, analytics, user management, all operational actions |

### Authentication

- JWT tokens with configurable expiration (default: 7 days)
- Password hashing via PBKDF2-SHA256 with application-level pepper
- Public registration limited to student and faculty roles
- Admin and facilities accounts are created via seed data or admin tooling only

### File Upload Security

- MIME type validation via Content-Type header
- Magic byte verification (actual file content, not just extension)
- Maximum file size enforcement (10MB)
- Server-generated filenames (user-controlled filenames never used)
- Authentication required for upload

### Data Integrity

- UUID-based report code generation (collision-safe)
- Enforced status transition graph (no arbitrary status manipulation)
- Database-level unique constraints on email and report codes
- Authorization checks on report detail access

---

## API Overview

### Authentication (`/api/v1/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register a new student/faculty account |
| POST | `/login` | Email + password login |
| POST | `/demo-login/{role}` | Passwordless demo login (student, faculty, facilities, admin) |
| GET | `/personas` | Public demo persona metadata |
| GET | `/meta` | Issue types, statuses, urgency levels |
| GET | `/users` | List users (authenticated) |
| GET | `/me` | Current user profile |

### Reports (`/api/v1/reports`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List reports with filtering, search, pagination |
| POST | `/` | Create a new report |
| GET | `/{id}` | Report detail (authorization-enforced) |
| POST | `/{id}/acknowledge` | Acknowledge a submitted report (facilities/admin) |
| PATCH | `/{id}/status` | Update report status with transition validation |
| POST | `/{id}/assign` | Assign report to facility worker (facilities/admin) |
| POST | `/{id}/resolve` | Mark report as resolved (facilities/admin) |
| POST | `/{id}/verify` | Reporter verifies resolution |
| POST | `/upload-photo` | Upload evidence image (authenticated) |

### Analytics (`/api/v1/analytics`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/overview` | Dashboard overview metrics |
| GET | `/hotspots` | Location-based hotspot analysis |
| GET | `/activity` | Full activity feed |
| GET | `/live-feed` | Recent activity feed |
| GET | `/charts-data` | Chart datasets for SVG rendering |

---

## Testing

```bash
# Run the full test suite (66 tests)
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/ -v -k "TestAuth"
python -m pytest tests/ -v -k "TestWorkflow"
python -m pytest tests/ -v -k "TestUpload"
```

### Test Coverage

- **Health**: Endpoint availability, homepage rendering
- **Authentication**: Valid/invalid login, JWT handling, missing credentials
- **Registration**: Valid registration, duplicate email, role escalation prevention
- **Demo Login**: Valid personas, invalid persona rejection, no silent fallback
- **RBAC**: Student restrictions, facilities permissions, admin permissions
- **Reports**: CRUD, filtering, pagination, search, validation
- **Workflow**: Full lifecycle, invalid transitions, verification rules
- **Upload**: Auth requirement, MIME validation, size limits, safe filenames
- **Analytics**: All endpoints, data integrity
- **Database**: Unique constraints, duplicate rejection

---

## Local Setup

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

## Demo Mode

Use the 1-Click Login toolbar in the application interface, or call the demo-login API:

```bash
# Login as student
curl -X POST http://localhost:8000/api/v1/auth/demo-login/student

# Login as facilities worker
curl -X POST http://localhost:8000/api/v1/auth/demo-login/facilities

# Login as admin
curl -X POST http://localhost:8000/api/v1/auth/demo-login/admin
```

These are **demo accounts** for the seeded Greenfield University campus. All passwords are `Password123!`.

| Role | Name | Email |
|------|------|-------|
| Student Reporter | Alex Rivera | `alex.student@greenfield.edu` |
| Facility Operations Worker | Marcus Vance | `marcus.worker@greenfield.edu` |
| Campus Administrator | Dr. Sarah Jenkins | `sarah.admin@greenfield.edu` |

---

## Known Limitations

- SQLite database (not suitable for production concurrency)
- File-based uploads (no cloud storage integration)
- Fixed password salt shared across all users (acceptable for demo; production should use per-user salts with bcrypt/argon2)
- CORS defaults to localhost only
- No email/notification delivery integration
- No automated deployment pipeline
- No real-time WebSocket updates (notification backend exists but no frontend inbox UI)

---

## Future Production Considerations

- Migrate to PostgreSQL for concurrent production use
- Implement per-user password hashing with bcrypt or argon2
- Add cloud storage for file uploads (S3, GCS)
- Implement email/notification delivery
- Add WebSocket support for real-time updates
- Add rate limiting and request throttling
- Implement API versioning strategy
- Add OpenAPI documentation customization
- Set up CI/CD pipeline with automated testing
- Add monitoring and observability (structured logging, metrics)

---

## Current Status

This is a functional portfolio demonstration. The application is fully operational for local development with seeded demo data. It demonstrates:

- Complete issue reporting workflow with photo uploads
- Role-based authentication and authorization with enforcement
- Interactive SVG campus map and analytics charts
- Reporter verification loop with auto-reopen
- Notification backend (database layer)
- Collision-safe report code generation
- Validated status transition graph
- Secure file upload with content verification
- 66 automated tests covering security, API, and workflow
