"""API route tests (no live database required)."""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_check():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "running"
    assert "version" in data


def test_diseases_list():
    r = client.get("/api/diseases")
    assert r.status_code == 200
    assert "diseases" in r.json()


def test_register_validation_short_password():
    r = client.post(
        "/api/auth/register",
        json={"full_name": "Test", "email": "t@example.com", "password": "123"},
    )
    assert r.status_code == 400


def test_login_invalid_credentials():
    r = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "wrongpass"},
    )
    assert r.status_code == 401


def test_admin_stats_requires_auth():
    r = client.get("/api/admin/stats")
    assert r.status_code in (401, 403)


def test_verify_email_missing_token():
    r = client.get("/api/auth/verify-email", params={"token": "invalid-token-xyz"})
    assert r.status_code == 400
