"""
Unit tests for API-04: Bearer Token Auth Implementation.
"""

import pytest
import os
from datetime import datetime, timedelta
from src.services.auth_service import AgentAuthService
from src.config.manager import config_manager

class TestAgentAuth:
    """Tests for local API token management."""

    @pytest.fixture
    def auth_service(self, monkeypatch):
        """Provides a clean auth service with mocked config."""
        # Ensure clean state in config
        monkeypatch.setattr(config_manager, "config", {"auth": {"api_tokens": {}}})
        return AgentAuthService()

    def test_token_generation(self, auth_service):
        """Verify tokens are generated with correct prefix and length."""
        token = auth_service.generate_agent_token("test_agent")
        
        assert token.startswith("as_")
        assert len(token) > 40
        assert token in auth_service._active_tokens

    def test_token_verification(self, auth_service):
        """Verify valid tokens pass and invalid ones fail."""
        token = auth_service.generate_agent_token("test_agent")
        
        assert auth_service.verify_token(token) is True
        assert auth_service.verify_token("invalid_token") is False
        assert auth_service.verify_token("") is False
        assert auth_service.verify_token(None) is False

    def test_token_expiration(self, auth_service):
        """Verify that expired tokens are rejected and pruned."""
        token = auth_service.generate_agent_token("expiring_agent")
        
        # Manually expire the token in memory
        auth_service._active_tokens[token] = datetime.utcnow() - timedelta(seconds=1)
        
        assert auth_service.verify_token(token) is False
        assert token not in auth_service._active_tokens

    def test_token_persistence(self, monkeypatch):
        """Verify tokens survive service re-initialization via config."""
        # 1. Generate token in first instance
        service1 = AgentAuthService()
        token = service1.generate_agent_token("persistent_agent")
        
        # 2. Re-initialize service
        service2 = AgentAuthService()
        
        # Should be loaded from 'persisted' config
        assert service2.verify_token(token) is True
        assert "persistent_agent" in config_manager.get("auth.api_tokens")[token]["label"]

    def test_invalid_token_cleanup(self, auth_service):
        """Verify that corrupted entries in config are handled gracefully."""
        config_manager.set("auth.api_tokens", {"bad_token": {"expiry": "not-a-date"}})
        
        # Re-load (should not crash)
        auth_service._load_persisted_tokens()
        assert "bad_token" not in auth_service._active_tokens
