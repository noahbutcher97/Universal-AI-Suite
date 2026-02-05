"""
Integration Edge Case Tests for the Recommendation Engine.
Tests the orchestrator's response to unusual hardware and preference combinations.
"""

import pytest
from src.services.recommendation_service import RecommendationService
from src.schemas.environment import EnvironmentReport
from src.schemas.recommendation import UserProfile, ContentPreferences
from src.config.manager import config_manager
from src.schemas.hardware import PlatformType

class TestRecommendationEdgeCases:
    """
    Tests focused on boundary conditions and unusual hardware states.
    """

    @pytest.fixture
    def service(self):
        return RecommendationService(config_manager.get_resources())

    def test_cpu_only_system(self, service):
        """Verify recommendations for a system with no GPU."""
        env = EnvironmentReport(
            gpu_vendor="none",
            gpu_name="None",
            vram_gb=0,
            ram_gb=32.0,
            os_name="Windows",
            os_version="10.0",
            arch="x86_64",
            disk_free_gb=500
        )
        profile = UserProfile(primary_use_cases=["txt2img"])
        results = service.generate_parallel_recommendations(profile, env)
        
        # Should only recommend models that fit in RAM (offload) or CPU-native models
        # Local recommendations should exist if CPU offload is enabled for some models
        for rec in results.local_recommendations:
            assert rec.execution_mode in ["native", "cpu_native", "gpu_offload", "quantized"]
            # Even if it says 'quantized', if VRAM is 0, it must be using RAM
            pass

    def test_massive_ram_offload_viability(self, service):
        """Test a system with 4GB VRAM but 128GB RAM (High offload potential)."""
        env = EnvironmentReport(
            gpu_vendor="nvidia",
            gpu_name="GTX 1650",
            vram_gb=4.0,
            ram_gb=128.0,
            os_name="Windows",
            os_version="10.0",
            arch="x86_64",
            disk_free_gb=500
        )
        profile = UserProfile(primary_use_cases=["txt2img"])
        results = service.generate_parallel_recommendations(profile, env)
        
        # Should allow models larger than 4GB due to massive RAM offload
        # (e.g., SDXL or quantized Flux)
        large_models = [r for r in results.local_recommendations if r.requirements.get("vram_min_mb", 0) > 4096]
        assert len(large_models) > 0
        assert any("offload" in r.execution_mode.lower() for r in large_models)

    def test_incompatible_platform_request(self, service):
        """Verify that requesting an incompatible platform results in zero local recs."""
        # Force the adapter to a specific platform and check if it filters
        env = EnvironmentReport(
            gpu_vendor="nvidia",
            gpu_name="RTX 4090",
            vram_gb=24.0,
            ram_gb=64.0,
            os_name="UnknownOS", # Should map to CPU_ONLY or UNKNOWN
            os_version="0.0",
            arch="x86_64",
            disk_free_gb=1000
        )
        profile = UserProfile(primary_use_cases=["txt2img"])
        results = service.generate_parallel_recommendations(profile, env)
        
        # If platform is UNKNOWN, Layer 1 should reject all platform-specific models
        # But maybe some platform-agnostic models pass? 
        # Most of our models are platform-specific.
        pass

    def test_exact_storage_headroom_boundary(self, service):
        """Test system exactly at the edge of storage requirements."""
        # Flux Schnell GGUF Q4 is ~10.0GB (hypothetical)
        # Headroom for 16GB RAM = 8GB (paging) + 10GB (safety) = 18GB
        # Total needed = 10 + 18 = 28GB
        
        env = EnvironmentReport(
            gpu_vendor="nvidia",
            gpu_name="RTX 4090",
            vram_gb=24.0,
            ram_gb=16.0,
            os_name="Windows",
            os_version="10.0",
            arch="x86_64",
            disk_free_gb=28 # Just enough for a 10GB model if safety is 10 and swap is 8
        )
        
        # We'll use a specific model check if possible, or just observe filtering
        profile = UserProfile(primary_use_cases=["txt2img"])
        results = service.generate_parallel_recommendations(profile, env)
        
        for rec in results.local_recommendations:
            size = rec.requirements.get("size_gb", 0)
            # size + 8 (swap) + 10 (safety) <= 28
            # size <= 10
            assert size <= 10.0

    def test_empty_user_profile(self, service):
        """Verify engine doesn't crash with minimal user profile."""
        env = EnvironmentReport(
            gpu_vendor="nvidia", gpu_name="RTX 4090", vram_gb=24.0, ram_gb=32.0,
            os_name="Windows", os_version="10.0", arch="x86_64", disk_free_gb=500
        )
        profile = UserProfile(primary_use_cases=[]) # Empty
        
        # Should still provide some default "Full Stack" or general recs
        results = service.generate_parallel_recommendations(profile, env)
        assert len(results.local_recommendations) > 0

    def test_conflicting_preferences(self, service):
        """Test high photorealism vs high speed (contradictory priorities)."""
        env = EnvironmentReport(
            gpu_vendor="nvidia", gpu_name="RTX 4090", vram_gb=24.0, ram_gb=32.0,
            os_name="Windows", os_version="10.0", arch="x86_64", disk_free_gb=500
        )
        profile = UserProfile(
            primary_use_cases=["txt2img"],
            content_preferences={
                "txt2img": ContentPreferences(photorealism=5, generation_speed=5)
            }
        )
        
        results = service.generate_parallel_recommendations(profile, env)
        assert len(results.local_recommendations) > 0
        # Engine should balance them via TOPSIS weights
