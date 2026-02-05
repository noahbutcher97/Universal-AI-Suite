"""
Unit tests for dependency-aware manifest generation.
"""

import pytest
from unittest.mock import MagicMock
from src.services.recommendation.manifest_orchestrator import ManifestOrchestrator
from src.schemas.recommendation import UserProfile
from src.services.recommendation.content_layer import ScoredCandidate, PassingCandidate
from src.services.recommendation.topsis_layer import RankedCandidate
from src.services.model_database import ModelEntry, ModelVariant

class TestManifestOrchestrator:
    """Tests for cascading dependency resolution."""

    @pytest.fixture
    def orchestrator(self):
        return ManifestOrchestrator(model_db=MagicMock())

    def test_basic_manifest_generation(self, orchestrator):
        """Verify that a simple model choice generates a manifest item."""
        # 1. Setup Mock Model
        model = ModelEntry(id="sd15", name="SD 1.5", category="image", family="sd", architecture={"vae": "sd_vae"})
        variant = ModelVariant(
            id="fp16", 
            precision="fp16", 
            vram_min_mb=4000, 
            vram_recommended_mb=6000, 
            download_size_gb=2.0, 
            download_url="http://sd15", 
            requires_nodes=["node_a"]
        )
        
        passing = PassingCandidate(model=model, variant=variant)
        scored = ScoredCandidate(passing_candidate=passing, similarity_score=0.9)
        ranked = RankedCandidate(scored_candidate=scored, closeness_coefficient=0.9, explanation="Test")
        
        # 2. Execute
        manifest = orchestrator.create_manifest([ranked], MagicMock(spec=UserProfile))
        
        # 3. Verify
        # Should have: Model, VAE, and Node_A
        assert len(manifest.items) >= 3
        ids = [item.item_id for item in manifest.items]
        assert "model_sd15_fp16" in ids
        assert "vae_sd_vae" in ids
        assert "node_node_a" in ids
        
        # Verify summary
        assert manifest.total_size_gb > 2.0
        assert manifest.estimated_time_minutes > 0

    def test_deduplication_in_manifest(self, orchestrator):
        """Verify that shared dependencies (like VAE) are only included once."""
        # Setup two models that both use 'sd_vae'
        model1 = ModelEntry(id="m1", name="M1", category="img", family="sd", architecture={"vae": "sd_vae"})
        model2 = ModelEntry(id="m2", name="M2", category="img", family="sd", architecture={"vae": "sd_vae"})
        
        v1 = ModelVariant(id="v1", precision="f16", vram_min_mb=4000, vram_recommended_mb=6000, download_size_gb=1.0)
        v2 = ModelVariant(id="v2", precision="f16", vram_min_mb=4000, vram_recommended_mb=6000, download_size_gb=1.0)
        
        r1 = RankedCandidate(scored_candidate=ScoredCandidate(passing_candidate=PassingCandidate(model=model1, variant=v1), similarity_score=0.8), closeness_coefficient=0.8)
        r2 = RankedCandidate(scored_candidate=ScoredCandidate(passing_candidate=PassingCandidate(model=model2, variant=v2), similarity_score=0.7), closeness_coefficient=0.7)
        
        manifest = orchestrator.create_manifest([r1, r2], MagicMock())
        
        # Count occurrences of vae_sd_vae
        vae_items = [i for i in manifest.items if i.item_id == "vae_sd_vae"]
        assert len(vae_items) == 1
