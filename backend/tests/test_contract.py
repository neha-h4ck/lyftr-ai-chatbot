from fastapi.testclient import TestClient
from app.main import app

def test_health_shape():
    # This test checks the route contract; runtime DB setup occurs in app lifespan.
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            body = response.json()
            assert body["status"] == "ok"
            assert "keys_configured" in body
            assert body["cache_enabled"] is True
