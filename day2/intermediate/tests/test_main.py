"""
Intermediate tests — no API calls, so these run in CI without spending money.
Focus: input validation and endpoint existence.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_returns_ok():
    """The /health endpoint must always return 200 {"status":"ok"}.
    Docker HEALTHCHECK depends on this — if it breaks, the container goes unhealthy."""
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_chat_requires_message_field():
    """FastAPI should reject requests missing the 'message' field with 422."""
    r = client.post("/chat", json={})
    assert r.status_code == 422


def test_chat_rejects_empty_body():
    """FastAPI should reject requests with no body at all with 422."""
    r = client.post("/chat")
    assert r.status_code == 422


def test_health_is_fast():
    """Health check must respond quickly — it runs every 30s in production."""
    import time
    start = time.time()
    r = client.get("/health")
    elapsed = time.time() - start
    assert r.status_code == 200
    assert elapsed < 1.0, f"Health check took {elapsed:.2f}s — too slow"
