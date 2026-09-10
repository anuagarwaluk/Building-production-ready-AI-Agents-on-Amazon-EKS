"""API contract tests for /chat that run without a model plane.

The happy path needs LiteLLM plus a backend, so end-to-end coverage lives
in scripts/test-chat.sh against a live cluster. These verify routing,
health, and input validation, which fail fast in CI without AWS.
"""

from fastapi.testclient import TestClient

from src.server import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_chat_rejects_empty_message():
    response = client.post("/chat", json={"message": "   "})
    assert response.status_code == 400


def test_chat_rejects_missing_message():
    response = client.post("/chat", json={})
    assert response.status_code == 422
