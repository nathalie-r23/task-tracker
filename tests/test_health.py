"""Tests for the health endpoint."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    """GET /health should return 200 and the expected JSON shape."""
    response = client.get("/health")

    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "notok"
    assert "timestamp" in body
    assert isinstance(body["timestamp"], str)
    assert body["timestamp"]  # non-empty