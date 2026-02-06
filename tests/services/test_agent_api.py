"""
Unit and Integration tests for the Local Agent API.
Verifies Health, Auth, and Rate Limiting.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app, auth_service

client = TestClient(app)

def test_health_check():
    """Verify public health endpoint is accessible."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_unauthorized_access():
    """Verify protected endpoints require a token."""
    response = client.get("/v1/system/status")
    # FastAPI's HTTPBearer returns 401 or 403 depending on config
    assert response.status_code in [401, 403]

def test_invalid_token_access():
    """Verify protected endpoints reject invalid tokens."""
    response = client.get(
        "/v1/system/status",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert "Invalid or expired" in response.json()["detail"]

def test_authorized_access():
    """Verify protected endpoints allow valid tokens."""
    # 1. Generate a token
    token_resp = client.get("/admin/token/new?label=test_client")
    token = token_resp.json()["token"]
    
    # 2. Use the token
    response = client.get(
        "/v1/system/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["os"] == "Windows"

def test_rate_limiting():
    """Verify that the API enforces rate limits."""
    # The middleware has a limit of 100 per minute in main.py
    # We'll trigger it by making many requests rapidly.
    # To keep the test fast, we could mock the middleware limit, 
    # but let's test the real thing with a small loop if possible.
    
    # Actually, let's create a separate TestClient with a smaller limit for testing
    from src.api.middleware.rate_limit import RateLimitMiddleware
    from fastapi import FastAPI
    
    test_app = FastAPI()
    test_app.add_middleware(RateLimitMiddleware, limit=5, window_secs=10)
    
    @test_app.get("/test")
    async def test_route():
        return {"ok": True}
        
    test_client = TestClient(test_app)
    
    # First 5 requests should pass
    for _ in range(5):
        resp = test_client.get("/test")
        assert resp.status_code == 200
        assert int(resp.headers["X-RateLimit-Remaining"]) >= 0
        
    # 6th request should be rate limited
    resp = test_client.get("/test")
    assert resp.status_code == 429
    assert resp.json()["detail"] == "Too many requests. Please slow down."
    
def test_rate_limit_reset():
    """Verify that rate limits reset after the window."""
    import time
    from src.api.middleware.rate_limit import RateLimitMiddleware
    from fastapi import FastAPI
    
    test_app = FastAPI()
    # 1 second window for fast testing
    test_app.add_middleware(RateLimitMiddleware, limit=2, window_secs=1)
    
    @test_app.get("/test")
    async def test_route():
        return {"ok": True}
        
    test_client = TestClient(test_app)
    
    assert test_client.get("/test").status_code == 200
    assert test_client.get("/test").status_code == 200
    assert test_client.get("/test").status_code == 429
    
    # Wait for reset
    time.sleep(1.1)
    
    assert test_client.get("/test").status_code == 200

def test_recommendation_integration():
    """Verify end-to-end API recommendation flow."""
    # 1. Get Token
    token_resp = client.get("/admin/token/new?label=integration_test")
    token = token_resp.json()["token"]
    
    # 2. POST Profile
    profile_data = {
        "primary_use_cases": ["txt2img"],
        "content_preferences": {
            "txt2img": {
                "photorealism": 5,
                "output_quality": 5
            }
        }
    }
    
    response = client.post(
        "/v1/recommendations/generate",
        json=profile_data,
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    results = response.json()
    assert "local_recommendations" in results
    assert len(results["local_recommendations"]) > 0
    # Top model should be high-quality (e.g. Flux or SDXL)
    assert "flux" in results["local_recommendations"][0]["display_name"].lower() or \
           "sdxl" in results["local_recommendations"][0]["display_name"].lower()
