import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Use a temporary database for tests so they don't depend on local state
_test_db_fd, _test_db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_path}"

from app.main import app
from app.database.session import engine, Base, SessionLocal
from app.database.seed import seed_database
from app.models.all_models import User, Campus, Report
from app.auth.security import hash_password, create_access_token

# Create schema and seed once per test session
Base.metadata.create_all(bind=engine)
seed_database()

client = TestClient(app)


@pytest.fixture(scope="session")
def db_session():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="session")
def seed_data(db_session):
    """Return seeded test data for use in tests."""
    campus = db_session.query(Campus).first()
    student = db_session.query(User).filter(User.email == "alex.student@greenfield.edu").first()
    worker = db_session.query(User).filter(User.email == "marcus.worker@greenfield.edu").first()
    admin = db_session.query(User).filter(User.email == "sarah.admin@greenfield.edu").first()
    faculty = db_session.query(User).filter(User.email == "priya.faculty@greenfield.edu").first()
    return {
        "campus": campus,
        "student": student,
        "worker": worker,
        "admin": admin,
        "faculty": faculty,
    }


def _login(role: str) -> dict:
    """Helper: demo-login and return headers dict."""
    res = client.post(f"/api/v1/auth/demo-login/{role}")
    assert res.status_code == 200, f"demo-login/{role} failed: {res.text}"
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def student_headers():
    return _login("student")


@pytest.fixture(scope="session")
def worker_headers():
    return _login("facilities")


@pytest.fixture(scope="session")
def admin_headers():
    return _login("admin")


@pytest.fixture(scope="session")
def faculty_headers():
    return _login("faculty")
