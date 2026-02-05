"""
Unit tests for CloudRecommendationLayer.

Per PLAN: Cloud API Integration - Tests for cloud pathway scoring,
cost sensitivity weights, and storage boost logic.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.recommendation.cloud_layer import (
    CloudRecommendationLayer,
    CloudScoringResult,
    WEIGHT_DISTRIBUTIONS,
    COST_THRESHOLDS,
    STORAGE_BOOST_THRESHOLD_GB,
    STORAGE_BOOST_MAX,
    MAJOR_PROVIDERS,
)
from src.schemas.recommendation import (
    UserProfile,
    CloudAPIPreferences,
    CloudRankedCandidate,
    ContentPreferences,
)
from src.schemas.model import (
    ModelEntry,
    ModelCapabilities,
    CloudInfo,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_model_db():
    """Create a mock ModelDatabase with test cloud models."""
    db = MagicMock()

    # Create test cloud models
    models = [
        _create_cloud_model(
            id="flux-pro-api",
            name="FLUX Pro API",
            provider="black_forest_labs",
            category="image_generation",
            partner_node=True,
            cost_per_gen=0.055,
        ),
        _create_cloud_model(
            id="dall-e-3",
            name="DALL-E 3",
            provider="openai",
            category="image_generation",
            partner_node=False,
            cost_per_gen=0.04,
        ),
        _create_cloud_model(
            id="sd3-turbo-api",
            name="SD3 Turbo API",
            provider="stability_ai",
            category="image_generation",
            partner_node=True,
            cost_per_gen=0.003,
        ),
        _create_cloud_model(
            id="expensive-model",
            name="Premium Model",
            provider="unknown",
            category="image_generation",
            partner_node=False,
            cost_per_gen=0.50,
        ),
    ]

    db.get_cloud_models.return_value = models
    return db


def _create_cloud_model(
    id: str,
    name: str,
    provider: str,
    category: str,
    partner_node: bool,
    cost_per_gen: float,
) -> ModelEntry:
    """Helper to create test cloud models."""
    return ModelEntry(
        id=id,
        name=name,
        category=category,
        family="api",
        provider=provider,
        is_cloud_api=True,
        cloud=CloudInfo(
            partner_node=partner_node,
            estimated_cost_per_generation=cost_per_gen,
        ),
        capabilities=ModelCapabilities(
            primary=["t2i", "text_to_image"],
            scores={"speed": 0.7, "photorealism": 0.8},
            style_strengths=["photorealistic", "digital_art"],
        ),
    )


@pytest.fixture
def user_profile_cost_sensitive():
    """User with high cost sensitivity."""
    return UserProfile(
        primary_use_cases=["content_generation"],
        cloud_api_preferences=CloudAPIPreferences(
            cloud_willingness="cloud_preferred",
            cost_sensitivity=5,
        ),
        content_preferences={
            "default": ContentPreferences(batch_frequency=3),
        },
    )


@pytest.fixture
def user_profile_quality_focused():
    """User who prioritizes quality over cost."""
    return UserProfile(
        primary_use_cases=["content_generation"],
        cloud_api_preferences=CloudAPIPreferences(
            cloud_willingness="cloud_preferred",
            cost_sensitivity=1,
        ),
        content_preferences={
            "default": ContentPreferences(batch_frequency=3),
        },
    )


@pytest.fixture
def user_profile_balanced():
    """User with balanced preferences (default)."""
    return UserProfile(
        primary_use_cases=["content_generation"],
        cloud_api_preferences=CloudAPIPreferences(
            cloud_willingness="cloud_fallback",
            cost_sensitivity=3,
        ),
    )


# =============================================================================
# Weight Distribution Tests
# =============================================================================

class TestWeightDistributions:
    """Tests for cost sensitivity weight distributions."""

    def test_all_sensitivity_levels_defined(self):
        """All 5 cost sensitivity levels should have weight distributions."""
        for level in range(1, 6):
            assert level in WEIGHT_DISTRIBUTIONS

    def test_weights_sum_to_one(self):
        """Each weight distribution should sum to 1.0."""
        for level, weights in WEIGHT_DISTRIBUTIONS.items():
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.01, f"Level {level} weights sum to {total}"

    def test_cost_weight_increases_with_sensitivity(self):
        """Cost efficiency weight should increase with cost sensitivity."""
        cost_weights = [
            WEIGHT_DISTRIBUTIONS[i]["cost_efficiency"]
            for i in range(1, 6)
        ]

        # Should generally increase (allow for small variations)
        assert cost_weights[4] > cost_weights[0]  # Level 5 > Level 1
        assert cost_weights[3] > cost_weights[1]  # Level 4 > Level 2

    def test_content_weight_decreases_with_sensitivity(self):
        """Content similarity weight should decrease with cost sensitivity."""
        content_weights = [
            WEIGHT_DISTRIBUTIONS[i]["content_similarity"]
            for i in range(1, 6)
        ]

        # Level 1 should have higher content weight than level 5
        assert content_weights[0] >= content_weights[4]


# =============================================================================
# Cloud Layer Initialization Tests
# =============================================================================

class TestCloudLayerInit:
    """Tests for CloudRecommendationLayer initialization."""

    def test_init_with_mock_db(self, mock_model_db):
        """Layer should accept custom model database."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        assert layer.model_db is mock_model_db

    def test_init_uses_singleton_if_none(self):
        """Layer should use singleton if no db provided."""
        with patch('src.services.recommendation.cloud_layer.get_model_database') as mock_get:
            mock_get.return_value = MagicMock()
            layer = CloudRecommendationLayer(model_db=None)
            mock_get.assert_called_once()


# =============================================================================
# Scoring Tests
# =============================================================================

class TestCloudScoring:
    """Tests for cloud model scoring."""

    def test_recommend_returns_candidates(self, mock_model_db, user_profile_balanced):
        """recommend() should return CloudRankedCandidate list."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        assert isinstance(results, list)
        assert all(isinstance(r, CloudRankedCandidate) for r in results)

    def test_recommend_scores_all_models(self, mock_model_db, user_profile_balanced):
        """All cloud models should be scored."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        assert len(results) == 4  # All 4 test models

    def test_recommend_sorted_by_score(self, mock_model_db, user_profile_balanced):
        """Results should be sorted by overall_score descending."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        scores = [r.overall_score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_partner_node_higher_provider_score(self, mock_model_db, user_profile_balanced):
        """Partner node models should have higher provider_score."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        # Find partner node and non-partner node models
        partner = next(r for r in results if r.setup_type == "partner_node")
        api_key = next(r for r in results if r.setup_type == "api_key")

        assert partner.provider_score > api_key.provider_score

    def test_cheaper_model_higher_cost_score(self, mock_model_db, user_profile_balanced):
        """Cheaper models should have higher cost_score."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        # SD3 Turbo ($0.003) should have higher cost score than FLUX Pro ($0.055)
        sd3 = next(r for r in results if r.model_id == "sd3-turbo-api")
        flux = next(r for r in results if r.model_id == "flux-pro-api")

        assert sd3.cost_score > flux.cost_score


# =============================================================================
# Cost Sensitivity Tests
# =============================================================================

class TestCostSensitivity:
    """Tests for cost sensitivity behavior."""

    def test_high_sensitivity_ranks_cheap_higher(
        self, mock_model_db, user_profile_cost_sensitive
    ):
        """High cost sensitivity should rank cheaper models higher."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_cost_sensitive)

        # SD3 Turbo ($0.003) should rank higher than expensive model ($0.50)
        sd3_idx = next(i for i, r in enumerate(results) if r.model_id == "sd3-turbo-api")
        expensive_idx = next(i for i, r in enumerate(results) if r.model_id == "expensive-model")

        assert sd3_idx < expensive_idx  # Lower index = higher rank

    def test_low_sensitivity_favors_quality(
        self, mock_model_db, user_profile_quality_focused
    ):
        """Low cost sensitivity should favor quality over cost."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_quality_focused)

        # Quality-focused user should see higher overall scores for quality models
        # (We expect FLUX Pro and DALL-E 3 to rank well due to provider reliability)
        top_result = results[0]
        assert top_result.provider in ["black_forest_labs", "openai", "stability_ai"]

    def test_high_sensitivity_soft_filters_expensive(
        self, mock_model_db, user_profile_cost_sensitive
    ):
        """High cost sensitivity should soft filter expensive models."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_cost_sensitive)

        # Expensive model should have penalty applied
        expensive = next(r for r in results if r.model_id == "expensive-model")

        # Check that expensive model has filtering reasoning
        assert any("filtered" in r.lower() or "exceeds" in r.lower()
                   for r in expensive.reasoning)


# =============================================================================
# Storage Boost Tests
# =============================================================================

class TestStorageBoost:
    """Tests for storage constraint boost logic."""

    def test_no_boost_above_threshold(self, mock_model_db, user_profile_balanced):
        """No boost should be applied when storage >= 50GB."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)

        results_plenty = layer.recommend(
            user_profile_balanced,
            storage_free_gb=100,
        )

        assert all(not r.storage_boost_applied for r in results_plenty)

    def test_boost_applied_below_threshold(self, mock_model_db, user_profile_balanced):
        """Boost should be applied when storage < 50GB."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)

        results_constrained = layer.recommend(
            user_profile_balanced,
            storage_free_gb=20,
        )

        assert all(r.storage_boost_applied for r in results_constrained)

    def test_boost_increases_scores(self, mock_model_db, user_profile_balanced):
        """Storage boost should increase overall scores."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)

        results_plenty = layer.recommend(
            user_profile_balanced,
            storage_free_gb=100,
        )
        results_constrained = layer.recommend(
            user_profile_balanced,
            storage_free_gb=20,
        )

        # Compare same model's scores
        flux_plenty = next(r for r in results_plenty if r.model_id == "flux-pro-api")
        flux_constrained = next(r for r in results_constrained if r.model_id == "flux-pro-api")

        assert flux_constrained.overall_score > flux_plenty.overall_score

    def test_boost_proportional_to_constraint(self, mock_model_db, user_profile_balanced):
        """Boost should be proportional to storage constraint severity."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)

        results_mild = layer.recommend(user_profile_balanced, storage_free_gb=40)
        results_severe = layer.recommend(user_profile_balanced, storage_free_gb=10)

        flux_mild = next(r for r in results_mild if r.model_id == "flux-pro-api")
        flux_severe = next(r for r in results_severe if r.model_id == "flux-pro-api")

        # Severe constraint should have higher boost
        assert flux_severe.overall_score > flux_mild.overall_score


# =============================================================================
# Category Filtering Tests
# =============================================================================

class TestCategoryFiltering:
    """Tests for category-based filtering."""

    def test_filter_by_category(self, mock_model_db, user_profile_balanced):
        """Models should be filtered by category."""
        # Add a video model to the mock
        video_model = _create_cloud_model(
            id="sora-api",
            name="Sora API",
            provider="openai",
            category="video_generation",
            partner_node=False,
            cost_per_gen=0.10,
        )
        mock_model_db.get_cloud_models.return_value.append(video_model)

        layer = CloudRecommendationLayer(model_db=mock_model_db)

        # Filter to image only
        results = layer.recommend(
            user_profile_balanced,
            categories=["image_generation"],
        )

        # Should not include video model
        model_ids = [r.model_id for r in results]
        assert "sora-api" not in model_ids


# =============================================================================
# Output Format Tests
# =============================================================================

class TestOutputFormat:
    """Tests for CloudRankedCandidate output format."""

    def test_candidate_has_all_scores(self, mock_model_db, user_profile_balanced):
        """Each candidate should have all scoring fields populated."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        for candidate in results:
            # Shared criteria
            assert 0.0 <= candidate.content_score <= 1.0
            assert 0.0 <= candidate.style_score <= 1.0
            assert 0.0 <= candidate.approach_score <= 1.0
            assert 0.0 <= candidate.ecosystem_score <= 1.0

            # Cloud-specific criteria
            assert 0.0 <= candidate.cost_score <= 1.0
            assert 0.0 <= candidate.provider_score <= 1.0
            assert 0.0 <= candidate.rate_limit_score <= 1.0
            assert 0.0 <= candidate.latency_score <= 1.0

    def test_candidate_has_cost_estimates(self, mock_model_db, user_profile_balanced):
        """Each candidate should have cost estimates."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        for candidate in results:
            assert candidate.estimated_cost_per_use >= 0
            assert candidate.estimated_monthly_cost >= 0

    def test_candidate_has_setup_type(self, mock_model_db, user_profile_balanced):
        """Each candidate should have setup_type."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        for candidate in results:
            assert candidate.setup_type in ["partner_node", "api_key"]

    def test_candidate_has_reasoning(self, mock_model_db, user_profile_balanced):
        """Each candidate should have reasoning list."""
        layer = CloudRecommendationLayer(model_db=mock_model_db)
        results = layer.recommend(user_profile_balanced)

        for candidate in results:
            assert isinstance(candidate.reasoning, list)


# =============================================================================
# Constants Tests
# =============================================================================

class TestConstants:
    """Tests for module constants."""

    def test_major_providers_includes_key_providers(self):
        """MAJOR_PROVIDERS should include key API providers."""
        assert "openai" in MAJOR_PROVIDERS
        assert "anthropic" in MAJOR_PROVIDERS
        assert "stability_ai" in MAJOR_PROVIDERS

    def test_cost_thresholds_defined(self):
        """Cost thresholds should be defined for all sensitivity levels."""
        for level in range(1, 6):
            assert level in COST_THRESHOLDS

    def test_cost_thresholds_decrease_with_sensitivity(self):
        """Cost thresholds should decrease with higher sensitivity."""
        # Level 5 should have stricter threshold than level 3
        assert COST_THRESHOLDS[5] < COST_THRESHOLDS[3]

    def test_storage_boost_constants(self):
        """Storage boost constants should be reasonable."""
        assert STORAGE_BOOST_THRESHOLD_GB == 50
        assert 0 < STORAGE_BOOST_MAX <= 0.5  # Max 50% boost is reasonable
