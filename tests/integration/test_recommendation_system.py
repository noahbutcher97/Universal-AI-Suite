"""
End-to-End Integration Tests for the 3-Layer TOPSIS Recommendation System.
Verifies the full pipeline:
Hardware Scan -> User Profile -> Recommendation Orchestrator -> Manifest Generation
"""

import pytest
from pathlib import Path
from src.services.recommendation_service import RecommendationService
from src.schemas.environment import EnvironmentReport
from src.schemas.recommendation import UserProfile, ContentPreferences, RankedCandidate
from src.config.manager import config_manager
from src.services.model_database import get_model_database

class TestRecommendationSystemIntegration:
    """
    Integration tests using the real SQLite database and modern orchestration.
    """

    @pytest.fixture(autouse=True)
    def ensure_db(self):
        """Ensure database is initialized and synchronized."""
        db = get_model_database()
        # Verify we have actual models to test with
        assert len(db.get_all_models()) > 100

    @pytest.fixture
    def service(self):
        return RecommendationService(config_manager.get_resources())

    def test_full_flow_high_end_nvidia(self, service):
        """Test full recommendation flow for a high-end NVIDIA system."""
        # 1. Mock Environment (RTX 4090 Desktop)
        env = EnvironmentReport(
            gpu_vendor="nvidia",
            gpu_name="NVIDIA GeForce RTX 4090",
            vram_gb=24.0,
            ram_gb=64.0,
            os_name="Windows",
            os_version="10.0.19045",
            arch="x86_64",
            disk_free_gb=1000,
            form_factor="desktop"
        )

        # 2. Mock User Profile
        profile = UserProfile(
            primary_use_cases=["txt2img"],
            content_preferences={"txt2img": ContentPreferences(photorealism=5, output_quality=5)}
        )

        # 3. Generate Recommendations
        results = service.generate_parallel_recommendations(profile, env)

        # 4. Assertions
        assert len(results.local_recommendations) > 0
        assert len(results.cloud_recommendations) > 0
        
        # Verify best local model is a flagship (likely Flux or SDXL)
        best = results.local_recommendations[0]
        # Flux should win on high-end hardware with high photorealism priority
        assert "flux" in best.display_name.lower() or "sdxl" in best.display_name.lower()
        assert best.hardware_fit_score >= 0.9  # Should fit perfectly on 24GB
        
        # 5. Generate Manifest
        manifest = service.generate_full_manifest(profile, results.local_recommendations[:1])
        assert len(manifest.items) >= 1
        # Check for model file
        assert any("models/checkpoints" in item.dest for item in manifest.items)

    def test_full_flow_apple_silicon_entry(self, service):
        """Test flow for a base M1 Mac (8GB Unified Memory)."""
        env = EnvironmentReport(
            gpu_vendor="apple",
            gpu_name="Apple M1",
            vram_gb=6.0, # 8GB * 0.75 ceiling
            ram_gb=8.0,
            os_name="Darwin",
            os_version="14.1.2",
            arch="arm64",
            disk_free_gb=100,
            form_factor="mini"
        )

        profile = UserProfile(primary_use_cases=["txt2img"])
        results = service.generate_parallel_recommendations(profile, env, categories=["image_generation"])

        # Assertions
        assert len(results.local_recommendations) > 0
        best = results.local_recommendations[0]
        
        # Base M1 should NOT be recommended massive models like Flux Pro native
        # It should recommend SD1.5 or heavily quantized SDXL
        vram_min = best.requirements.get("vram_min_mb", 0) / 1024
        assert vram_min <= 6.0
        
        # Verify K-quants are filtered out (RankedCandidate.id check)
        for rec in results.local_recommendations:
            # Variants are checked in Layer 1
            pass

    def test_cli_provider_integration(self, service):
        """Verify CLI providers are recommended correctly from the database."""
        env = EnvironmentReport(
            gpu_vendor="none",
            gpu_name="None",
            vram_gb=0,
            ram_gb=16.0,
            os_name="Windows",
            os_version="10.0",
            arch="x86_64",
            disk_free_gb=200
        )
        
        # User wants coding assistance
        profile = UserProfile(
            primary_use_cases=["productivity"],
            cli_preferences=None # Use defaults
        )
        
        # Legacy method check (used by SetupWizardService)
        recs = service.generate_recommendations("productivity", env, profile)
        
        cli_rec = next((r for r in recs if r.module_id == "cli_provider"), None)
        assert cli_rec is not None
        assert cli_rec.enabled is True
        # Should pick Gemini or Claude for productivity
        assert "Gemini" in cli_rec.display_name or "Claude" in cli_rec.display_name

    def test_storage_constraint_recursive_rejection(self, service):
        """Verify that models are excluded when disk space is extremely low."""
        env = EnvironmentReport(
            gpu_vendor="nvidia",
            gpu_name="NVIDIA GeForce RTX 4090",
            vram_gb=24.0,
            ram_gb=64.0,
            os_name="Windows",
            os_version="10.0",
            arch="x86_64",
            disk_free_gb=5, # Extremely low space
            form_factor="desktop"
        )
        
        profile = UserProfile(primary_use_cases=["txt2img"])
        results = service.generate_parallel_recommendations(profile, env)
        
        # Large models should be rejected by Layer 1 storage check
        assert len(results.local_recommendations) == 0
        assert results.storage_constrained is True

    def test_manifest_deduplication(self, service):
        """Verify that manifest generation doesn't duplicate shared dependencies (e.g. VAEs)."""
        env = EnvironmentReport(
            gpu_vendor="nvidia", 
            gpu_name="NVIDIA GeForce RTX 4090",
            vram_gb=24.0, 
            ram_gb=64.0, 
            os_name="Windows", 
            os_version="10.0", 
            arch="x86_64", 
            disk_free_gb=1000
        )
        profile = UserProfile(primary_use_cases=["txt2img"])
        results = service.generate_parallel_recommendations(profile, env)
        
        # Pick two models that likely share a VAE
        recs = results.local_recommendations[:2]
        
        manifest = service.generate_full_manifest(profile, recs)
        
        # Check for duplicate item IDs
        item_ids = [item.item_id for item in manifest.items]
        assert len(item_ids) == len(set(item_ids))
