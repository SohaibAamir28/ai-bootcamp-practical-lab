from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_returns_ok():
    """The /health endpoint must return 200 and {"status": "ok"}.
    This is what the Docker HEALTHCHECK pings — it must never break."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
