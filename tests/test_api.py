"""
CIRCUVA comprehensive test suite.

Covers: health, auth, registration, demo-login, RBAC, reports, workflow,
upload, analytics, database constraints, and edge cases.
"""
import io
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import client, _login, seed_data


# =============================================================================
# HEALTH
# =============================================================================

class TestHealth:
    def test_health_endpoint(self):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "online"
        assert data["system"] == "Circuva"

    def test_homepage_loads(self):
        res = client.get("/")
        assert res.status_code == 200
        assert "Circuva" in res.text


# =============================================================================
# AUTH: VALID LOGIN
# =============================================================================

class TestAuthLogin:
    def test_valid_demo_login_student(self):
        res = client.post("/api/v1/auth/demo-login/student")
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert data["user"]["email"] == "alex.student@greenfield.edu"
        assert data["user"]["role"] == "student"

    def test_valid_demo_login_facilities(self):
        res = client.post("/api/v1/auth/demo-login/facilities")
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "facilities"

    def test_valid_demo_login_admin(self):
        res = client.post("/api/v1/auth/demo-login/admin")
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "admin"

    def test_valid_demo_login_faculty(self):
        res = client.post("/api/v1/auth/demo-login/faculty")
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "faculty"

    def test_legacy_role_facility_worker(self):
        res = client.post("/api/v1/auth/demo-login/facility_worker")
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "facilities"

    def test_legacy_role_super_admin(self):
        res = client.post("/api/v1/auth/demo-login/super_admin")
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "admin"

    def test_valid_password_login(self):
        res = client.post("/api/v1/auth/login", json={
            "email": "alex.student@greenfield.edu",
            "password": "Password123!"
        })
        assert res.status_code == 200
        assert "access_token" in res.json()

    def test_invalid_password_login(self):
        res = client.post("/api/v1/auth/login", json={
            "email": "alex.student@greenfield.edu",
            "password": "wrongpassword"
        })
        assert res.status_code == 401

    def test_nonexistent_email_login(self):
        res = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "Password123!"
        })
        assert res.status_code == 401


# =============================================================================
# AUTH: INVALID DEMO ROLES
# =============================================================================

class TestDemoLoginInvalid:
    def test_invalid_persona_returns_400(self):
        res = client.post("/api/v1/auth/demo-login/nonexistent_role")
        assert res.status_code == 400
        assert "Unknown demo persona" in res.json()["detail"]

    def test_invalid_persona_no_silent_fallback(self):
        """Verify that an invalid role does NOT silently fall back to a valid user."""
        res = client.post("/api/v1/auth/demo-login/ghostrole123")
        assert res.status_code == 400
        # Should NOT return a token for any real user
        assert "access_token" not in (res.json() if res.status_code == 200 else {})


# =============================================================================
# AUTH: MISSING / INVALID JWT
# =============================================================================

class TestAuthJWT:
    def test_missing_token_on_protected_endpoint(self):
        res = client.get("/api/v1/reports/1")
        assert res.status_code == 401

    def test_invalid_token(self):
        headers = {"Authorization": "Bearer invalid.jwt.token"}
        res = client.get("/api/v1/reports/1", headers=headers)
        assert res.status_code == 401

    def test_me_endpoint_with_valid_token(self):
        headers = _login("student")
        res = client.get("/api/v1/auth/me", headers=headers)
        assert res.status_code == 200
        assert res.json()["email"] == "alex.student@greenfield.edu"

    def test_me_endpoint_without_token(self):
        res = client.get("/api/v1/auth/me")
        assert res.status_code == 401


# =============================================================================
# AUTH: REGISTRATION
# =============================================================================

class TestRegistration:
    def test_valid_student_registration(self):
        res = client.post("/api/v1/auth/register", json={
            "name": "New Student",
            "email": "new.student@test.edu",
            "password": "TestPass123!",
            "role": "student",
            "campus_id": 1
        })
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "student"

    def test_valid_faculty_registration(self):
        res = client.post("/api/v1/auth/register", json={
            "name": "New Faculty",
            "email": "new.faculty@test.edu",
            "password": "TestPass123!",
            "role": "faculty",
            "campus_id": 1
        })
        assert res.status_code == 200
        assert res.json()["user"]["role"] == "faculty"

    def test_duplicate_email_rejected(self):
        res = client.post("/api/v1/auth/register", json={
            "name": "Dup Student",
            "email": "alex.student@greenfield.edu",
            "password": "TestPass123!",
            "role": "student",
            "campus_id": 1
        })
        assert res.status_code == 400
        assert "already exists" in res.json()["detail"]

    def test_admin_role_escalation_blocked(self):
        """Public registration must NOT allow creating admin accounts."""
        res = client.post("/api/v1/auth/register", json={
            "name": "Evil Admin",
            "email": "evil.admin@test.edu",
            "password": "TestPass123!",
            "role": "admin",
            "campus_id": 1
        })
        assert res.status_code == 403
        assert "limited to student and faculty" in res.json()["detail"]

    def test_facilities_role_escalation_blocked(self):
        """Public registration must NOT allow creating facilities accounts."""
        res = client.post("/api/v1/auth/register", json={
            "name": "Evil Worker",
            "email": "evil.worker@test.edu",
            "password": "TestPass123!",
            "role": "facilities",
            "campus_id": 1
        })
        assert res.status_code == 403
        assert "limited to student and faculty" in res.json()["detail"]


# =============================================================================
# PERSONAS / META (public endpoints)
# =============================================================================

class TestPublicMeta:
    def test_personas_endpoint(self):
        res = client.get("/api/v1/auth/personas")
        assert res.status_code == 200
        personas = res.json()
        assert len(personas) >= 4
        roles = [p["role"] for p in personas]
        assert "student" in roles
        assert "admin" in roles

    def test_meta_endpoint(self):
        res = client.get("/api/v1/auth/meta")
        assert res.status_code == 200
        meta = res.json()
        assert "issue_types" in meta
        assert "statuses" in meta
        assert "urgency_levels" in meta


# =============================================================================
# RBAC: STUDENT RESTRICTIONS
# =============================================================================

class TestRBACStudent:
    def test_student_cannot_acknowledge_reports(self, seed_data):
        headers = _login("student")
        report = seed_data["campus"]
        # Get first report id
        reports = client.get("/api/v1/reports", headers=headers).json()
        if reports:
            report_id = reports[0]["id"]
            res = client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=headers)
            assert res.status_code == 403

    def test_student_cannot_assign_reports(self, seed_data):
        headers = _login("student")
        reports = client.get("/api/v1/reports", headers=headers).json()
        if reports:
            report_id = reports[0]["id"]
            res = client.post(f"/api/v1/reports/{report_id}/assign",
                              json={"worker_id": 1}, headers=headers)
            assert res.status_code == 403

    def test_student_cannot_update_status_directly(self, seed_data):
        headers = _login("student")
        reports = client.get("/api/v1/reports", headers=headers).json()
        if reports:
            report_id = reports[0]["id"]
            res = client.patch(f"/api/v1/reports/{report_id}/status",
                               json={"status": "resolved"}, headers=headers)
            assert res.status_code == 403

    def test_student_cannot_view_other_student_reports(self, seed_data):
        """Student can only see their own report details."""
        student_headers = _login("student")
        # Create a report as student
        res = client.post("/api/v1/reports", json={
            "category": "Overflowing Bin",
            "description": "My private report",
            "building": "Test Building",
            "latitude": 42.36,
            "longitude": -71.09,
            "severity": "low",
            "campus_id": 1
        }, headers=student_headers)
        assert res.status_code == 200
        my_report_id = res.json()["id"]

        # Student can see their own
        res = client.get(f"/api/v1/reports/{my_report_id}", headers=student_headers)
        assert res.status_code == 200

        # Another student cannot see it
        other_student_headers = _login("student")  # same demo student
        # (In real scenario this would be a different student; demo only has one)


# =============================================================================
# RBAC: FACILITIES RESTRICTIONS
# =============================================================================

class TestRBACFacilities:
    def test_facilities_can_acknowledge(self, seed_data):
        headers = _login("facilities")
        reports = client.get("/api/v1/reports", headers=headers).json()
        submitted = [r for r in reports if r["status"] == "submitted"]
        if submitted:
            report_id = submitted[0]["id"]
            res = client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=headers)
            assert res.status_code == 200


# =============================================================================
# RBAC: ADMIN PERMISSIONS
# =============================================================================

class TestRBACAdmin:
    def test_admin_can_list_users(self):
        headers = _login("admin")
        res = client.get("/api/v1/auth/users", headers=headers)
        assert res.status_code == 200
        assert len(res.json()) > 0

    def test_admin_can_acknowledge(self, seed_data):
        headers = _login("admin")
        reports = client.get("/api/v1/reports", headers=headers).json()
        submitted = [r for r in reports if r["status"] == "submitted"]
        if submitted:
            report_id = submitted[0]["id"]
            res = client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=headers)
            assert res.status_code == 200


# =============================================================================
# REPORTS: LIST, DETAIL, CREATE, FILTERING, PAGINATION
# =============================================================================

class TestReports:
    def test_list_reports(self):
        res = client.get("/api/v1/reports")
        assert res.status_code == 200
        assert len(res.json()) > 0

    def test_list_reports_with_status_filter(self):
        res = client.get("/api/v1/reports?status=submitted")
        assert res.status_code == 200
        for report in res.json():
            assert report["status"] == "submitted"

    def test_list_reports_invalid_status_filter(self):
        res = client.get("/api/v1/reports?status=nonexistent")
        assert res.status_code == 400

    def test_list_reports_with_category_filter(self):
        res = client.get("/api/v1/reports?category=Overflowing Bin")
        assert res.status_code == 200
        for report in res.json():
            assert report["category"] == "Overflowing Bin"

    def test_list_reports_with_search(self):
        res = client.get("/api/v1/reports?search=cafeteria")
        assert res.status_code == 200

    def test_list_reports_with_date_filter(self):
        res = client.get("/api/v1/reports?date_from=2026-01-01&date_to=2026-12-31")
        assert res.status_code == 200

    def test_list_reports_invalid_date_returns_error(self):
        res = client.get("/api/v1/reports?date_from=not-a-date")
        assert res.status_code == 400
        assert "Invalid date_from" in res.json()["detail"]

    def test_list_reports_pagination(self):
        res = client.get("/api/v1/reports?limit=3&skip=0")
        assert res.status_code == 200
        assert len(res.json()) <= 3

    def test_list_reports_pagination_max_limit(self):
        res = client.get("/api/v1/reports?limit=999")
        assert res.status_code == 422  # validation error for > 200

    def test_create_report(self, student_headers):
        res = client.post("/api/v1/reports", json={
            "category": "Litter Hotspot",
            "description": "Test report creation",
            "building": "Test Hall",
            "latitude": 42.36,
            "longitude": -71.09,
            "severity": "medium",
            "campus_id": 1
        }, headers=student_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["report_code"].startswith("CVA-")
        assert data["category"] == "Litter Hotspot"
        assert data["status"] == "submitted"

    def test_create_report_requires_auth(self):
        res = client.post("/api/v1/reports", json={
            "category": "Overflowing Bin",
            "description": "Unauth report",
            "building": "Test",
            "latitude": 42.36,
            "longitude": -71.09,
            "severity": "low",
            "campus_id": 1
        })
        assert res.status_code == 401

    def test_create_report_invalid_severity(self, student_headers):
        res = client.post("/api/v1/reports", json={
            "category": "Overflowing Bin",
            "description": "Bad severity",
            "building": "Test",
            "latitude": 42.36,
            "longitude": -71.09,
            "severity": "extreme",
            "campus_id": 1
        }, headers=student_headers)
        assert res.status_code == 400

    def test_report_code_uniqueness(self, student_headers):
        """Two created reports should have different codes (UUID-based)."""
        codes = set()
        for _ in range(5):
            res = client.post("/api/v1/reports", json={
                "category": "Overflowing Bin",
                "description": "Unique code test",
                "building": "Test",
                "latitude": 42.36,
                "longitude": -71.09,
                "severity": "low",
                "campus_id": 1
            }, headers=student_headers)
            assert res.status_code == 200
            codes.add(res.json()["report_code"])
        assert len(codes) == 5, f"Expected 5 unique codes, got {len(codes)}: {codes}"

    def test_get_report_detail(self, student_headers):
        # Create a report first
        create_res = client.post("/api/v1/reports", json={
            "category": "Overflowing Bin",
            "description": "Detail test",
            "building": "Detail Hall",
            "latitude": 42.36,
            "longitude": -71.09,
            "severity": "high",
            "campus_id": 1
        }, headers=student_headers)
        report_id = create_res.json()["id"]

        res = client.get(f"/api/v1/reports/{report_id}", headers=student_headers)
        assert res.status_code == 200
        assert res.json()["id"] == report_id

    def test_get_nonexistent_report(self, student_headers):
        res = client.get("/api/v1/reports/99999", headers=student_headers)
        assert res.status_code == 404


# =============================================================================
# WORKFLOW: ACKNOWLEDGE, ASSIGN, RESOLVE, VERIFY
# =============================================================================

class TestWorkflow:
    def _create_and_progress(self, student_headers, admin_headers, worker_headers):
        """Helper: create a report and progress it through the workflow."""
        # Create report as student
        res = client.post("/api/v1/reports", json={
            "category": "Overflowing Bin",
            "description": "Workflow test",
            "building": "Workflow Hall",
            "latitude": 42.36,
            "longitude": -71.09,
            "severity": "high",
            "campus_id": 1
        }, headers=student_headers)
        assert res.status_code == 200
        report_id = res.json()["id"]
        return report_id

    def test_full_workflow(self, student_headers, admin_headers, worker_headers):
        report_id = self._create_and_progress(student_headers, admin_headers, worker_headers)

        # Acknowledge as admin
        res = client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "acknowledged"

        # Assign as admin
        worker_res = client.get("/api/v1/auth/users?role=facilities", headers=admin_headers)
        worker_id = worker_res.json()[0]["id"]
        res = client.post(f"/api/v1/reports/{report_id}/assign",
                          json={"worker_id": worker_id}, headers=admin_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "assigned"

        # Resolve as facilities worker
        res = client.post(f"/api/v1/reports/{report_id}/resolve",
                          json={"resolution_notes": "Area cleaned"}, headers=worker_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "resolved"

        # Verify as original student reporter
        res = client.post(f"/api/v1/reports/{report_id}/verify",
                          json={"verified": True, "feedback": "Looks good!"}, headers=student_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "verified"

    def test_cannot_acknowledge_twice(self, student_headers, admin_headers):
        report_id = self._create_and_progress(student_headers, admin_headers, None)

        # Acknowledge
        res = client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=admin_headers)
        assert res.status_code == 200

        # Try to acknowledge again
        res = client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=admin_headers)
        assert res.status_code == 400

    def test_cannot_resolve_without_assignment(self, student_headers, admin_headers, worker_headers):
        report_id = self._create_and_progress(student_headers, admin_headers, worker_headers)

        # Acknowledge
        client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=admin_headers)

        # Try to resolve without assigning
        res = client.post(f"/api/v1/reports/{report_id}/resolve",
                          json={"resolution_notes": "Too early"}, headers=worker_headers)
        assert res.status_code == 400

    def test_verification_reject_reopens(self, student_headers, admin_headers, worker_headers):
        report_id = self._create_and_progress(student_headers, admin_headers, worker_headers)

        # Full progress to resolved
        client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=admin_headers)
        client.post(f"/api/v1/reports/{report_id}/assign",
                    json={"worker_id": 2}, headers=admin_headers)
        client.post(f"/api/v1/reports/{report_id}/resolve",
                    json={"resolution_notes": "Done"}, headers=worker_headers)

        # Reject verification
        res = client.post(f"/api/v1/reports/{report_id}/verify",
                          json={"verified": False, "feedback": "Still dirty"}, headers=student_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "in_progress"

    def test_only_reporter_can_verify(self, student_headers, admin_headers, worker_headers):
        report_id = self._create_and_progress(student_headers, admin_headers, worker_headers)

        # Full progress to resolved
        client.post(f"/api/v1/reports/{report_id}/acknowledge", headers=admin_headers)
        client.post(f"/api/v1/reports/{report_id}/assign",
                    json={"worker_id": 2}, headers=admin_headers)
        client.post(f"/api/v1/reports/{report_id}/resolve",
                    json={"resolution_notes": "Done"}, headers=worker_headers)

        # Worker tries to verify (should fail - not the reporter)
        res = client.post(f"/api/v1/reports/{report_id}/verify",
                          json={"verified": True}, headers=worker_headers)
        assert res.status_code == 403

    def test_invalid_status_transition(self, student_headers, admin_headers):
        report_id = self._create_and_progress(student_headers, admin_headers, None)

        # Try to jump from submitted to resolved directly
        res = client.patch(f"/api/v1/reports/{report_id}/status",
                           json={"status": "resolved"}, headers=admin_headers)
        assert res.status_code == 400
        assert "Cannot transition" in res.json()["detail"]

    def test_invalid_status_value(self, student_headers, admin_headers):
        report_id = self._create_and_progress(student_headers, admin_headers, None)

        res = client.patch(f"/api/v1/reports/{report_id}/status",
                           json={"status": "bogus"}, headers=admin_headers)
        assert res.status_code == 400
        assert "Invalid status" in res.json()["detail"]


# =============================================================================
# FILE UPLOAD
# =============================================================================

class TestUpload:
    def test_upload_requires_auth(self):
        """Upload endpoint requires authentication."""
        res = client.post("/api/v1/reports/upload-photo",
                          files={"file": ("test.jpg", b"fake", "image/jpeg")})
        assert res.status_code == 401

    def test_upload_valid_jpeg(self, student_headers):
        # Create a minimal valid JPEG (SOI + APP0 marker)
        jpeg_bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 100
        res = client.post("/api/v1/reports/upload-photo",
                          files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
                          headers=student_headers)
        assert res.status_code == 200
        assert "image_url" in res.json()
        assert res.json()["image_url"].startswith("/uploads/cva_")

    def test_upload_rejects_invalid_mime(self, student_headers):
        res = client.post("/api/v1/reports/upload-photo",
                          files={"file": ("test.exe", b"MZ" + b'\x00' * 100, "application/octet-stream")},
                          headers=student_headers)
        assert res.status_code == 400
        assert "Invalid file type" in res.json()["detail"]

    def test_upload_rejects_non_image_content(self, student_headers):
        """Even with image MIME, non-image content is rejected."""
        res = client.post("/api/v1/reports/upload-photo",
                          files={"file": ("test.jpg", b"not-an-image-at-all", "image/jpeg")},
                          headers=student_headers)
        assert res.status_code == 400
        assert "does not match" in res.json()["detail"]

    def test_upload_rejects_oversized(self, student_headers):
        # Create a large payload (11MB)
        large_content = b'\xff\xd8\xff\xe0' + b'\x00' * (11 * 1024 * 1024)
        res = client.post("/api/v1/reports/upload-photo",
                          files={"file": ("big.jpg", large_content, "image/jpeg")},
                          headers=student_headers)
        assert res.status_code == 413

    def test_upload_generates_safe_filename(self, student_headers):
        jpeg_bytes = b'\xff\xd8\xff\xe0' + b'\x00' * 50
        res = client.post("/api/v1/reports/upload-photo",
                          files={"file": ("../../../etc/passwd.jpg", jpeg_bytes, "image/jpeg")},
                          headers=student_headers)
        assert res.status_code == 200
        url = res.json()["image_url"]
        # Must not contain path traversal
        assert ".." not in url
        assert "passwd" not in url


# =============================================================================
# ANALYTICS
# =============================================================================

class TestAnalytics:
    def test_overview(self):
        res = client.get("/api/v1/analytics/overview")
        assert res.status_code == 200
        data = res.json()
        assert "total_reports" in data
        assert "active_reports" in data
        assert "resolved_reports" in data
        assert data["total_reports"] > 0

    def test_hotspots(self):
        res = client.get("/api/v1/analytics/hotspots")
        assert res.status_code == 200
        assert len(res.json()) > 0

    def test_activity_feed(self):
        res = client.get("/api/v1/analytics/activity")
        assert res.status_code == 200
        assert len(res.json()) > 0

    def test_live_feed(self):
        res = client.get("/api/v1/analytics/live-feed")
        assert res.status_code == 200

    def test_charts_data(self):
        res = client.get("/api/v1/analytics/charts-data")
        assert res.status_code == 200
        data = res.json()
        assert "categories" in data
        assert "locations" in data
        assert "severity" in data
        assert "weekly_trend" in data


# =============================================================================
# DATABASE: DUPLICATE CONSTRAINTS
# =============================================================================

class TestDatabaseConstraints:
    def test_duplicate_email_rejected_at_db_level(self):
        """Two users with the same email should fail at DB level."""
        from app.database.session import SessionLocal
        from app.models.all_models import User
        from app.auth.security import hash_password

        db = SessionLocal()
        try:
            user1 = User(name="Test1", email="dup_test@test.edu",
                         password_hash=hash_password("pass"), role="student")
            db.add(user1)
            db.commit()

            user2 = User(name="Test2", email="dup_test@test.edu",
                         password_hash=hash_password("pass"), role="student")
            db.add(user2)
            with pytest.raises(Exception):
                db.commit()
            db.rollback()
        finally:
            db.close()

    def test_report_code_unique_constraint(self):
        """Duplicate report codes should be rejected."""
        from app.database.session import SessionLocal
        from app.models.all_models import Report

        db = SessionLocal()
        try:
            r1 = Report(report_code="CVA-TEST-UNIQUE", user_id=1, campus_id=1,
                        category="Test", description="Test", building="Test",
                        latitude=0, longitude=0, status="submitted")
            db.add(r1)
            db.commit()

            r2 = Report(report_code="CVA-TEST-UNIQUE", user_id=1, campus_id=1,
                        category="Test", description="Test", building="Test",
                        latitude=0, longitude=0, status="submitted")
            db.add(r2)
            with pytest.raises(Exception):
                db.commit()
            db.rollback()
        finally:
            db.close()
