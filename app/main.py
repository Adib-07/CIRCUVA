import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.core.config import settings
from app.database.session import engine, Base
from app.database.seed import seed_database
from app.api.auth_router import router as auth_router
from app.api.reports_router import router as reports_router
from app.api.analytics_router import router as analytics_router

# Initialize database schema and seed demo data on startup
Base.metadata.create_all(bind=engine)
try:
    seed_database()
except Exception as e:
    print(f"Seed note: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="See it. Report it. Resolve it. — Commercial Campus Environmental Operations SaaS Platform",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
UPLOADS_DIR = settings.UPLOAD_DIR

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Serve static assets without caching so the browser always fetches the
# current CSS/JS. Without this, a stale cached stylesheet can render the page
# as unstyled raw text (e.g. the mobile nav appearing as a duplicate row).
class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, Response):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

# Mount static and upload directories
app.mount("/static", NoCacheStaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(reports_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)

@app.get("/")
def render_index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"photography": settings.DEMO_PHOTOGRAPHY}
    )

@app.get("/health")
def health_check():
    return {"status": "online", "system": "Circuva", "version": "1.0.0"}
