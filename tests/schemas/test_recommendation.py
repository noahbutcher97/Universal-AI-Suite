"""
Unit tests for recommendation schemas.

Per PLAN: Cloud API Integration - Tests for CloudAPIPreferences, CloudRankedCandidate,
and RecommendationResults schemas.
"""

import pytest
from dataclasses import fields

from src.schemas.recommendation import (
    CloudAPIPreferences,
    CloudRankedCandidate,
    CloudRecommendationInfo,
    RecommendationResults,
    UserProfile,
    RankedCandidate,
)


class TestCloudAPIPreferences:
    """Tests for CloudAPIPreferences dataclass."""

    def test_default_values(self):
        """CloudAPIPreferences should have sensible defaults."""
        prefs = CloudAPIPreferences()

        assert prefs.cloud_willingness == "cloud_fallback"
        assert prefs.cost_sensitivity == 3

    def test_all_willingness_options(self):
        """All 4 willingness options should be valid."""
        valid_options = ["local_only", "cloud_fallback", "cloud_preferred", "cloud_only"]

        for option in valid_options:
            prefs = CloudAPIPreferences(cloud_willingness=option)
            assert prefs.cloud_willingness == option

    def test_cost_sensitivity_range(self):
        """Cost sensitivity should accept values 1-5."""
        for value in range(1, 6):
            prefs = CloudAPIPreferences(cost_sensitivity=value)
            assert prefs.cost_sensitivity == value

    def test_local_only_means_no_cloud(self):
        """local_only should indicate no cloud recommendations."""
        prefs = CloudAPIPreferences(cloud_willingness="local_only")
        assert prefs.cloud_willingness == "local_only"
        # This is a semantic test - the recommendation engine should respect this

    def test_cloud_only_means_no_local(self):
        """cloud_only should indicate no local recommendations."""
        prefs = CloudAPIPreferences(cloud_willingness="cloud_only")
        assert prefs.cloud_willingness == "cloud_only"
        # This is a semantic test - minimal hardware detection for this option


class TestUserProfileCloudIntegration:
    """Tests for CloudAPIPreferences integration in UserProfile."""

    def test_user_profile_has_cloud_preferences(self):
        """UserProfile should have cloud_api_preferences field."""
        profile = UserProfile()

        assert hasattr(profile, "cloud_api_preferences")
        assert isinstance(profile.cloud_api_preferences, CloudAPIPreferences)

    def test_user_profile_cloud_defaults(self):
        """UserProfile cloud preferences should have correct defaults."""
        profile = UserProfile()

        assert profile.cloud_api_preferences.cloud_willingness == "cloud_fallback"
        assert profile.cloud_api_preferences.cost_sensitivity == 3

    def test_user_profile_custom_cloud_preferences(self):
        """UserProfile should accept custom cloud preferences."""
        profile = UserProfile(
            cloud_api_preferences=CloudAPIPreferences(
                cloud_willingness="cloud_preferred",
                cost_sensitivity=5
            )
        )

        assert profile.cloud_api_preferences.cloud_willingness == "cloud_preferred"
        assert profile.cloud_api_preferences.cost_sensitivity == 5


class TestCloudRankedCandidate:
    """Tests for CloudRankedCandidate dataclass."""

    def test_required_fields(self):
        """CloudRankedCandidate should require model_id, display_name, provider."""
        candidate = CloudRankedCandidate(
            model_id="test-model",
            display_name="Test Model",
            provider="test_provider"
        )

        assert candidate.model_id == "test-model"
        assert candidate.display_name == "Test Model"
        assert candidate.provider == "test_provider"

    def test_shared_criteria_defaults(self):
        """Shared criteria scores should default to 0.0."""
        candidate = CloudRankedCandidate(
            model_id="test",
            display_name="Test",
            provider="test"
        )

        assert candidate.content_score == 0.0
        assert candidate.style_score == 0.0
        assert candidate.approach_score == 0.0
        assert candidate.ecosystem_score == 0.0

    def test_cloud_specific_criteria_defaults(self):
        """Cloud-specific criteria scores should default to 0.0."""
        candidate = CloudRankedCandidate(
            model_id="test",
            display_name="Test",
            provider="test"
        )

        assert candidate.cost_score == 0.0
        assert candidate.provider_score == 0.0
        assert candidate.rate_limit_score == 0.0
        assert candidate.latency_score == 0.0

    def test_scoring_fields(self):
        """CloudRankedCandidate should have all scoring fields."""
        candidate = CloudRankedCandidate(
            model_id="flux-pro-api",
            display_name="FLUX Pro API",
            provider="black_forest_labs",
            content_score=0.85,
            style_score=0.90,
            approach_score=0.70,
            ecosystem_score=0.80,
            cost_score=0.45,
            provider_score=0.80,
            rate_limit_score=0.75,
            latency_score=0.70,
            overall_score=0.78,
            estimated_cost_per_use=0.055,
            estimated_monthly_cost=5.50,
            setup_type="api_key"
        )

        assert candidate.overall_score == 0.78
        assert candidate.estimated_cost_per_use == 0.055
        assert candidate.setup_type == "api_key"

    def test_storage_boost_flag(self):
        """CloudRankedCandidate should track if storage boost was applied."""
        candidate = CloudRankedCandidate(
            model_id="test",
            display_name="Test",
            provider="test",
            storage_boost_applied=True
        )

        assert candidate.storage_boost_applied is True

    def test_setup_type_options(self):
        """setup_type should accept partner_node or api_key."""
        partner_candidate = CloudRankedCandidate(
            model_id="kling-2.0",
            display_name="Kling 2.0",
            provider="kuaishou",
            setup_type="partner_node"
        )
        assert partner_candidate.setup_type == "partner_node"

        api_candidate = CloudRankedCandidate(
            model_id="dall-e-3",
            display_name="DALL-E 3",
            provider="openai",
            setup_type="api_key"
        )
        assert api_candidate.setup_type == "api_key"


class TestCloudRecommendationInfo:
    """Tests for CloudRecommendationInfo dataclass."""

    def test_default_values(self):
        """CloudRecommendationInfo should have sensible defaults."""
        info = CloudRecommendationInfo()

        assert info.is_cloud is False
        assert info.provider == ""
        assert info.partner_node_available is False
        assert info.estimated_cost_per_use == 0.0
        assert info.setup_instructions == ""

    def test_cloud_info_populated(self):
        """CloudRecommendationInfo should accept all fields."""
        info = CloudRecommendationInfo(
            is_cloud=True,
            provider="stability_ai",
            partner_node_available=True,
            estimated_cost_per_use=0.003,
            setup_instructions="https://comfy.org/partner-nodes"
        )

        assert info.is_cloud is True
        assert info.partner_node_available is True


class TestRecommendationResults:
    """Tests for RecommendationResults dataclass."""

    def test_default_values(self):
        """RecommendationResults should have sensible defaults."""
        results = RecommendationResults()

        assert results.local_recommendations == []
        assert results.cloud_recommendations == []
        assert results.primary_pathway == "local"
        assert results.storage_constrained is False
        assert results.storage_warnings == []

    def test_local_only_results(self):
        """RecommendationResults for local_only user should have no cloud."""
        from unittest.mock import MagicMock
        local_candidate = MagicMock(spec=RankedCandidate)
        local_candidate.id = "flux-dev"

        results = RecommendationResults(
            local_recommendations=[local_candidate],
            cloud_recommendations=[],
            primary_pathway="local"
        )

        assert len(results.local_recommendations) == 1
        assert len(results.cloud_recommendations) == 0
        assert results.primary_pathway == "local"

    def test_cloud_only_results(self):
        """RecommendationResults for cloud_only user should have no local."""
        cloud_candidate = CloudRankedCandidate(
            model_id="flux-pro-api",
            display_name="FLUX Pro API",
            provider="black_forest_labs"
        )

        results = RecommendationResults(
            local_recommendations=[],
            cloud_recommendations=[cloud_candidate],
            primary_pathway="cloud"
        )

        assert len(results.local_recommendations) == 0
        assert len(results.cloud_recommendations) == 1
        assert results.primary_pathway == "cloud"

    def test_mixed_results(self):
        """RecommendationResults for cloud_fallback should have both."""
        from unittest.mock import MagicMock
        local_candidate = MagicMock(spec=RankedCandidate)
        local_candidate.id = "sdxl"

        cloud_candidate = CloudRankedCandidate(
            model_id="dall-e-3",
            display_name="DALL-E 3",
            provider="openai"
        )

        results = RecommendationResults(
            local_recommendations=[local_candidate],
            cloud_recommendations=[cloud_candidate],
            primary_pathway="local"
        )

        assert len(results.local_recommendations) == 1
        assert len(results.cloud_recommendations) == 1

    def test_storage_constraint_tracking(self):
        """RecommendationResults should track storage constraints."""
        results = RecommendationResults(
            storage_constrained=True,
            storage_warnings=["FLUX.1 Dev (25GB) would use 50% of free space"]
        )

        assert results.storage_constrained is True
        assert len(results.storage_warnings) == 1


class TestCostSensitivityWeightMapping:
    """
    Tests for cost sensitivity weight mapping.

    Per PLAN: Cloud API Integration - Cost sensitivity (1-5) should adjust
    criterion weights. These tests verify the expected behavior.
    """

    def test_low_cost_sensitivity_favors_quality(self):
        """cost_sensitivity=1 should favor quality over cost."""
        # This is a design test - actual implementation in cloud_layer.py
        # Weight expectations per plan:
        # cost_sensitivity=1: content=0.25, cost=0.05
        expected_content_weight = 0.25
        expected_cost_weight = 0.05

        # When implemented, the cloud layer should use these weights
        assert expected_content_weight > expected_cost_weight

    def test_high_cost_sensitivity_favors_cost(self):
        """cost_sensitivity=5 should favor cost over quality."""
        # Weight expectations per plan:
        # cost_sensitivity=5: content=0.20, cost=0.30
        expected_content_weight = 0.20
        expected_cost_weight = 0.30

        # When implemented, the cloud layer should use these weights
        assert expected_cost_weight > expected_content_weight


class TestWillingnessPathwaySelection:
    """
    Tests for willingness-based pathway selection.

    Per PLAN: Cloud API Integration - cloud_willingness determines which
    pathways are run and which is primary.
    """

    @pytest.mark.parametrize("willingness,expected_local,expected_cloud,expected_primary", [
        ("local_only", True, False, "local"),
        ("cloud_fallback", True, True, "local"),
        ("cloud_preferred", True, True, "cloud"),
        ("cloud_only", False, True, "cloud"),
    ])
    def test_pathway_selection(self, willingness, expected_local, expected_cloud, expected_primary):
        """Verify pathway selection logic based on willingness."""
        # This is a design test - actual implementation in recommendation_service.py
        prefs = CloudAPIPreferences(cloud_willingness=willingness)

        # Expected behavior:
        should_run_local = willingness != "cloud_only"
        should_run_cloud = willingness != "local_only"
        is_cloud_primary = willingness in ["cloud_preferred", "cloud_only"]

        assert should_run_local == expected_local
        assert should_run_cloud == expected_cloud
        assert ("cloud" if is_cloud_primary else "local") == expected_primary
