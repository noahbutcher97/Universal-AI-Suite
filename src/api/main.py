"""
Main entry point for the AI Universal Suite Local Agent API.
Part of Task API-01 and SYS-04.

Features:
- Bearer Token Auth (Task API-04)
- Rate Limiting (Task API-03)
- Unified Error Handling
"""

import time
from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware.rate_limit import RateLimitMiddleware
from src.services.auth_service import AgentAuthService
from src.services.system_service import SystemService
from src.services.recommendation_service import RecommendationService
from src.schemas.recommendation import UserProfile, RecommendationResults
from src.config.manager import config_manager
from src.utils.logger import log

# Initialize Services
auth_service = AgentAuthService()
system_service = SystemService()
recommendation_service = RecommendationService(config_manager.get_resources())
security = HTTPBearer()

app = FastAPI(
    title="AI Universal Suite Local Agent",
    description="REST API for local AI workstation management and mobile sync.",
    version="1.0.0"
)

# 1. CORS Middleware (Allow local frontend/mobile dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Rate Limiting Middleware (Task API-03)
app.add_middleware(RateLimitMiddleware, limit=100, window_secs=60)

# Security Dependency
async def verify_agent_auth(auth: HTTPAuthorizationCredentials = Security(security)):
    """Verifies the Bearer token."""
    if not auth_service.verify_token(auth.credentials):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired agent token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth.credentials

# --- Public Endpoints ---

@app.get("/health", tags=["System"])
async def health_check():
    """Verify API is alive."""
    return {"status": "ok", "timestamp": time.time(), "agent": "AI Universal Suite"}

# --- Protected Endpoints (Mock/Placeholder for API-01) ---

@app.get("/v1/system/status", tags=["System"], dependencies=[Depends(verify_agent_auth)])
async def get_system_status():
    """Get high-level hardware/software status."""
    report = system_service.scan_full_environment()
    return {
        "os": report.os_name,
        "gpu": report.gpu_name,
        "vram_gb": report.vram_gb,
        "ram_gb": report.ram_gb,
        "storage_free_gb": report.disk_free_gb,
        "tier": report.recommended_model_tier,
        "api_active": True
    }

@app.post("/v1/recommendations/generate", tags=["Recommendation"], response_model=RecommendationResults, dependencies=[Depends(verify_agent_auth)])
async def generate_recommendations(profile: UserProfile):
    """Trigger a new recommendation run using real hardware scan."""
    env = system_service.scan_full_environment()
    results = recommendation_service.generate_parallel_recommendations(profile, env)
    return results

# --- Admin Endpoints ---

@app.get("/admin/token/new", tags=["Admin"])
async def get_new_token(label: str = "local_dev"):
    """
    Generate a new agent token (In production, this would be guarded by 
    local filesystem access or user confirmation).
    """
    token = auth_service.generate_agent_token(label)
    return {"token": token, "type": "bearer", "label": label}
