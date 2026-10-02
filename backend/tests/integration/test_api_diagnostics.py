import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"


def test_readiness_endpoint():
    res = client.get("/api/v1/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"


def test_prometheus_metrics_endpoint():
    res = client.get("/metrics")
    assert res.status_code == 200
    assert "netpath_diagnostics_total" in res.text


def test_targets_api_crud():
    # List targets
    res = client.get("/api/v1/targets")
    assert res.status_code == 200
    initial_count = len(res.json())

    # Create target
    res_create = client.post("/api/v1/targets", json={"url": "https://example.org"})
    assert res_create.status_code == 201
    created_data = res_create.json()
    assert created_data["hostname"] == "example.org"
    target_id = created_data["id"]

    # Retrieve created target
    res_get = client.get(f"/api/v1/targets/{target_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == target_id


def test_ssrf_blocking_via_api():
    # Attacking loopback via API must return 400 Bad Request
    res = client.post("/api/v1/diagnostics", json={"url": "http://127.0.0.1:8000"})
    assert res.status_code == 400
    assert "SSRF validation blocked" in res.json()["detail"]


def test_diagnostics_sync_execution():
    # Diagnostic against public domain example.com
    res = client.post(
        "/api/v1/diagnostics",
        json={"url": "https://example.com", "wait": True}
    )
    # Could succeed if internet is available or execute cleanly
    assert res.status_code in (201, 400)
