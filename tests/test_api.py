from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "online"

def test_login_demo():
    res = client.post("/api/v1/auth/demo-login/student")
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alex.student@greenfield.edu"

def test_get_reports():
    res = client.get("/api/v1/reports")
    assert res.status_code == 200
    reports = res.json()
    assert len(reports) > 0

def test_create_report():
    # Login first
    login_res = client.post("/api/v1/auth/demo-login/student")
    token = login_res.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "category": "Overflowing Bin",
        "description": "Test overflow report in quad",
        "building": "Engineering Block B Quad",
        "latitude": 42.3595,
        "longitude": -71.0950,
        "severity": "high",
        "campus_id": 1
    }
    
    res = client.post("/api/v1/reports", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["report_code"].startswith("CVA-")
    assert data["category"] == "Overflowing Bin"

def test_analytics():
    res = client.get("/api/v1/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_reports"] > 0
    
    res_hot = client.get("/api/v1/analytics/hotspots")
    assert res_hot.status_code == 200
    assert len(res_hot.json()) > 0

    res_feed = client.get("/api/v1/analytics/live-feed")
    assert res_feed.status_code == 200
    assert len(res_feed.json()) > 0

if __name__ == "__main__":
    test_health()
    test_login_demo()
    test_get_reports()
    test_create_report()
    test_analytics()
    print("All automated API tests passed successfully!")
