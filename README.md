# Circuva

> **See it. Report it. Resolve it.**
> Closing the loop on campus environmental operations.

Circuva is a commercial-grade, production-ready SaaS web platform that empowers students and staff to report campus environmental issues, while enabling campus administrators and facility operations teams to manage dispatch, resolve incidents, verify cleanups, and analyze spatial operational hotspots.

---

## 🌟 Key Features

- **Commercial SaaS Design & Branding**: Deep charcoal, off-white, and emerald palette with modern glassmorphism headers, real photography from Unsplash, and responsive UI.
- **Floating Live Campus Status Panel**: Live demo statistics showing daily reports, resolved count, in-progress items, and critical alerts.
- **Interactive Campus Map**: Leaflet.js map with color-coded severity markers, building labels, and incident details popups.
- **Multi-Step Issue Reporting Wizard**: 5-step intuitive flow (Category Picker, Building/GPS Location, Severity Rating, Evidence Photo Upload with preview, Summary & unique `CVA-2026-XXXXXX` code generation).
- **Interactive Before/After Slider**: Visual image comparison component showcasing campus transformation after cleanup.
- **Role-Based Portals & Dashboards**:
  - **Student / Staff Dashboard**: View submitted reports, track status timelines, and earn Impact Score points.
  - **Admin Operations Dashboard**: Live Incident Feed, Chart.js analytics (Categories, Locations, Weekly Trend, Severity), Waste Hotspots with trend indicators, and Worker Dispatching.
  - **Facility Operations Team Dashboard**: View assigned tasks, accept jobs, upload resolution proof photos, and mark resolved.
- **Reporter Verification Loop**: Closed-loop resolution confirmation ("Was this problem fixed?") that auto-reopens rejected tasks and notifies administrators.

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Environment Setup & Installation
```bash
# Navigate to project directory
cd campus-waste-reporter

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Seed Database & Run Server
```bash
# Seed Greenfield University demo data
python -m app.database.seed

# Start the uvicorn development server
uvicorn app.main:app --reload --port 8000
```
Open your browser at `http://localhost:8000`.

---

## 🔑 Demo Personas & Quick Login

Use the 1-Click Login toolbar at the top of the interface:

| Role | Demo User | Email | Password |
|---|---|---|---|
| **Student Reporter** | Alex Rivera | `alex.student@greenfield.edu` | `Password123!` |
| **Facility Operations Worker** | Marcus Vance | `marcus.worker@greenfield.edu` | `Password123!` |
| **Campus Administrator** | Dr. Sarah Jenkins | `sarah.admin@greenfield.edu` | `Password123!` |

---

## 📁 Project Architecture

```
campus-waste-reporter/
├── app/
│   ├── api/                # FastAPI Routers (Auth, Reports, Analytics)
│   ├── auth/               # Password hashing, JWT & RBAC Middlewares
│   ├── core/               # App configuration & photography registry
│   ├── database/           # DB session & Greenfield University seeder
│   ├── models/             # SQLAlchemy DB Entities
│   ├── schemas/            # Pydantic Schemas
│   └── main.py             # FastAPI App Entrypoint
├── static/
│   ├── css/styles.css      # SaaS Design System & Styling
│   └── js/app.js           # Frontend Interactive Controller
├── templates/
│   └── index.html          # HTML5 Application Template
├── uploads/                # Local evidence & resolution image storage
├── .env.example
├── requirements.txt
└── README.md
```
