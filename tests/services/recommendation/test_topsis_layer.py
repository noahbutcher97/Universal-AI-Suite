"""
Unit tests for Layer 3: TOPSIS Multi-Criteria Ranking.

Tests the TOPSIS algorithm implementation per SPEC_v3 Section 6.4.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

from src.services.recommendation.topsis_layer import TOPSISLayer
from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
    FormFactorProfile,
    StorageProfile,
    StorageTier,
    RAMProfile,
)
from src.schemas.recommendation import (
    CriterionScore,
    RankedCandidate,
    ScoredCandidate,
    FeatureMatch,
    PassingCandidate,
    UserProfile,
    ContentPreferences
)


# --- Mock Objects ---


@dataclass
class MockCapabilities:
    """Mock model capabilities."""
    scores: Dict[str, float] = field(default_factory=dict)
    style_strengths: List[str] = field(default_factory=list)


@dataclass
class MockDependencies:
    """Mock model dependencies."""
    required_nodes: List[str] = field(default_factory=list)
    paired_models: List[str] = field(default_factory=list)


@dataclass
class MockCloud:
    """Mock cloud support."""
    partner_node: bool = False
    replicate: Optional[str] = None


@dataclass
class MockModelVariant:
    """Mock model variant."""
    id: str = "fp16"
    precision: str = "fp16"
    vram_min_mb: int = 6000
    vram_recommended_mb: int = 8000


@dataclass
class MockModelEntry:
    """Mock model entry."""
    id: str = "test_model"
    name: str = "Test Model"
    family: str = "sdxl"
    capabilities: MockCapabilities = field(default_factory=MockCapabilities)
    dependencies: MockDependencies = field(default_factory=MockDependencies)
    cloud: MockCloud = field(default_factory=MockCloud)


def create_mock_candidate(
    model_id: str = "test_model",
    model_name: str = "Test Model",
    family: str = "sdxl",
    similarity_score: float = 0.8,
    vram_min_mb: int = 6000,
    vram_recommended_mb: int = 8000,
    speed_score: float = 0.7,
    required_nodes: List[str] = None,
) -> ScoredCandidate:
    """Create a mock ScoredCandidate for testing."""
    model = MockModelEntry(
        id=model_id,
        name=model_name,
        family=family,
        capabilities=MockCapabilities(scores={"speed": speed_score}),
        dependencies=MockDependencies(required_nodes=required_nodes or []),
        cloud=MockCloud(partner_node=True),
    )
    variant = MockModelVariant(
        vram_min_mb=vram_min_mb,
        vram_recommended_mb=vram_recommended_mb,
    )
    passing = PassingCandidate(
        model=model,
        variant=variant,
        execution_mode="native",
        warnings=[],
    )
    return ScoredCandidate(
        passing_candidate=passing,
        similarity_score=similarity_score,
        matching_features=[],
        style_match_bonus=0.0,
    )


def create_mock_hardware(
    vram_gb: float = 12.0,
    is_laptop: bool = False,
    storage_tier: StorageTier = StorageTier.FAST,
) -> HardwareProfile:
    """Create a mock HardwareProfile for testing."""
    # Map storage tier to type string for StorageProfile
    storage_type_map = {
        StorageTier.FAST: "nvme_gen4",
        StorageTier.MODERATE: "sata_ssd",
        StorageTier.SLOW: "hdd",
    }
    return HardwareProfile(
        platform=PlatformType.WINDOWS_NVIDIA,
        gpu_vendor="nvidia",
        gpu_name="NVIDIA GeForce RTX 4080",
        vram_gb=vram_gb,
        compute_capability=8.9,
        form_factor=FormFactorProfile(
            is_laptop=is_laptop,
            sustained_performance_ratio=0.6 if is_laptop else 1.0,
        ),
        storage=StorageProfile(
            path="C:\\",
            total_gb=500.0,
            free_gb=200.0,
            storage_type=storage_type_map.get(storage_tier, "nvme_gen4"),
            estimated_read_mbps=5000 if storage_tier == StorageTier.FAST else 500,
            tier=storage_tier,
        ),
        ram=RAMProfile(
            total_gb=32.0,
            available_gb=24.0,
            usable_for_offload_gb=16.0,
        ),
    )


def create_mock_user_profile(
    speed_priority: int = 3,
    prefer_simple: int = 3,
    technical_exp: int = 3,
) -> UserProfile:
    """Create a mock UserProfile for testing."""
    return UserProfile(
        technical_experience=technical_exp,
        prefer_simple_setup=prefer_simple,
        primary_use_cases=["txt2img"],
        content_preferences={
            "txt2img": ContentPreferences(generation_speed=speed_priority),
        },
    )


# --- Test Classes ---


class TestTOPSISLayerInit:
    """Tests for TOPSISLayer initialization."""

    def test_default_weights(self):
        """Should use default weights if none provided."""
        layer = TOPSISLayer()
        assert layer.weights["content_similarity"] == 0.35
        assert layer.weights["hardware_fit"] == 0.25
        assert layer.weights["speed_fit"] == 0.15
        assert layer.weights["ecosystem_maturity"] == 0.15
        assert layer.weights["approach_fit"] == 0.10

    def test_custom_weights(self):
        """Should accept custom weights."""
        custom = {"content_similarity": 0.5, "hardware_fit": 0.5}
        layer = TOPSISLayer(weights=custom)
        assert layer.weights["content_similarity"] == 0.5
        assert layer.weights["hardware_fit"] == 0.5


class TestContentSimilarityScoring:
    """Tests for content similarity scoring."""

    def test_content_similarity_includes_style_bonus(self):
        """Content similarity should include style match bonus."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(similarity_score=0.8)
        candidate.style_match_bonus = 0.1

        score = layer._score_content_similarity(candidate)

        assert score == 0.9  # 0.8 + 0.1


class TestHardwareFitScoring:
    """Tests for hardware fit scoring."""

    def test_hardware_fit_full_score_when_vram_exceeds_recommended(self):
        """Should return 1.0 when VRAM exceeds recommended."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(
            vram_min_mb=6000,
            vram_recommended_mb=8000,
        )
        hardware = create_mock_hardware(vram_gb=12.0)  # 12288 MB

        score = layer._score_hardware_fit(candidate, hardware)

        assert score == 1.0

    def test_hardware_fit_partial_score_between_min_and_recommended(self):
        """Should interpolate when VRAM between min and recommended."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(
            vram_min_mb=6000,
            vram_recommended_mb=10000,  # 4GB gap
        )
        hardware = create_mock_hardware(vram_gb=8.0)  # 8192 MB - in the middle

        score = layer._score_hardware_fit(candidate, hardware)

        # Should be between 0.5 and 1.0
        assert 0.5 < score < 1.0

    def test_hardware_fit_laptop_penalty(self):
        """Should apply laptop penalty."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(
            vram_min_mb=6000,
            vram_recommended_mb=8000,
        )
        hardware = create_mock_hardware(vram_gb=12.0, is_laptop=True)

        score = layer._score_hardware_fit(candidate, hardware)

        # Laptop penalty reduces score
        assert score < 1.0

    def test_hardware_fit_reduced_laptop_penalty_high_performance(self):
        """Laptop penalty should be reduced if sustained performance is high."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(
            vram_min_mb=6000,
            vram_recommended_mb=8000,
        )

        hardware_low = create_mock_hardware(vram_gb=12.0, is_laptop=True)
        hardware_low.form_factor.sustained_performance_ratio = 0.5

        hardware_high = create_mock_hardware(vram_gb=12.0, is_laptop=True)
        hardware_high.form_factor.sustained_performance_ratio = 0.8

        score_low = layer._score_hardware_fit(candidate, hardware_low)
        score_high = layer._score_hardware_fit(candidate, hardware_high)

        # Higher sustained performance = less penalty
        assert score_high > score_low


class TestSpeedFitScoring:
    """Tests for speed fit scoring."""

    def test_speed_fit_uses_model_speed_score(self):
        """Should use model's speed score."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(speed_score=0.9)
        hardware = create_mock_hardware()
        user_profile = create_mock_user_profile()

        score = layer._score_speed_fit(candidate, hardware, user_profile)

        assert score > 0.5  # Should be high for fast model

    def test_speed_fit_storage_penalty_slow(self):
        """Should penalize slow storage."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(speed_score=0.8)
        hardware = create_mock_hardware(storage_tier=StorageTier.SLOW)
        user_profile = create_mock_user_profile()

        score = layer._score_speed_fit(candidate, hardware, user_profile)

        # Should have penalty
        assert score < 0.8

    def test_speed_fit_high_priority_boosts_fast_models(self):
        """High speed priority should boost fast models."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(speed_score=0.8)
        hardware = create_mock_hardware()
        user_profile = create_mock_user_profile(speed_priority=5)

        score = layer._score_speed_fit(candidate, hardware, user_profile)

        # High priority with fast model = high score
        assert score > 0.7


class TestEcosystemMaturityScoring:
    """Tests for ecosystem maturity scoring."""

    def test_ecosystem_maturity_popular_family_bonus(self):
        """Popular families should get bonus."""
        layer = TOPSISLayer()
        candidate_popular = create_mock_candidate(family="sdxl")
        candidate_niche = create_mock_candidate(family="obscure_model")

        score_popular = layer._score_ecosystem_maturity(candidate_popular)
        score_niche = layer._score_ecosystem_maturity(candidate_niche)

        assert score_popular > score_niche

    def test_ecosystem_maturity_fewer_nodes_bonus(self):
        """Fewer required nodes should give bonus."""
        layer = TOPSISLayer()
        candidate_simple = create_mock_candidate(required_nodes=[])
        candidate_complex = create_mock_candidate(
            required_nodes=["node1", "node2", "node3"]
        )

        score_simple = layer._score_ecosystem_maturity(candidate_simple)
        score_complex = layer._score_ecosystem_maturity(candidate_complex)

        assert score_simple > score_complex


class TestApproachFitScoring:
    """Tests for approach fit scoring."""

    def test_approach_fit_simple_user_prefers_simple_model(self):
        """Users preferring simple should score simple models higher."""
        layer = TOPSISLayer()
        candidate_simple = create_mock_candidate(required_nodes=[])
        candidate_complex = create_mock_candidate(
            required_nodes=["node1", "node2", "node3"]
        )
        user_profile = create_mock_user_profile(prefer_simple=5)

        score_simple = layer._score_approach_fit(candidate_simple, user_profile)
        score_complex = layer._score_approach_fit(candidate_complex, user_profile)

        assert score_simple > score_complex

    def test_approach_fit_expert_slightly_prefers_complex(self):
        """Expert users should slightly prefer complex models."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(required_nodes=[])
        user_profile = create_mock_user_profile(technical_exp=5, prefer_simple=1)

        score = layer._score_approach_fit(candidate, user_profile)

        # Expert with complex preference should not heavily penalize simple
        assert score > 0.5


class TestMatrixOperations:
    """Tests for TOPSIS matrix operations."""

    def test_normalize_matrix_vector_normalization(self):
        """Should normalize using vector normalization."""
        layer = TOPSISLayer()
        matrix = [
            {"a": 3.0, "b": 4.0},
            {"a": 0.0, "b": 3.0},
        ]

        normalized = layer._normalize_matrix(matrix)

        # Check normalization: sqrt(3^2 + 0^2) = 3, sqrt(4^2 + 3^2) = 5
        assert abs(normalized[0]["a"] - 1.0) < 0.01  # 3/3 = 1
        assert abs(normalized[0]["b"] - 0.8) < 0.01  # 4/5 = 0.8
        assert abs(normalized[1]["a"] - 0.0) < 0.01  # 0/3 = 0
        assert abs(normalized[1]["b"] - 0.6) < 0.01  # 3/5 = 0.6

    def test_apply_weights(self):
        """Should multiply by weights."""
        layer = TOPSISLayer()
        layer.weights = {"a": 0.5, "b": 0.25}
        normalized = [{"a": 0.8, "b": 0.6}]

        weighted = layer._apply_weights(normalized)

        assert weighted[0]["a"] == 0.4  # 0.8 * 0.5
        assert weighted[0]["b"] == 0.15  # 0.6 * 0.25


class TestClosenessComputation:
    """Tests for closeness coefficient computation."""

    def test_compute_closeness_single_candidate(self):
        """Single candidate should get closeness of 0.5."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate()
        weighted = [{"a": 0.5, "b": 0.5}]

        ranked = layer._compute_closeness([candidate], weighted)

        # With only one candidate, it is both ideal and anti-ideal
        # d+ = 0, d- = 0, so closeness = 0.5 (defined behavior)
        assert len(ranked) == 1
        assert ranked[0].closeness_coefficient == 0.5

    def test_compute_closeness_two_candidates(self):
        """Best candidate should have highest closeness."""
        layer = TOPSISLayer()
        candidates = [
            create_mock_candidate(model_id="best"),
            create_mock_candidate(model_id="worst"),
        ]
        weighted = [
            {"a": 0.9, "b": 0.9},  # Best
            {"a": 0.1, "b": 0.1},  # Worst
        ]

        ranked = layer._compute_closeness(candidates, weighted)

        # Best should have higher closeness
        best_cc = [r for r in ranked if r.scored_candidate.passing_candidate.model.id == "best"][0]
        worst_cc = [r for r in ranked if r.scored_candidate.passing_candidate.model.id == "worst"][0]

        assert best_cc.closeness_coefficient > worst_cc.closeness_coefficient


class TestRanking:
    """Tests for full ranking."""

    def test_rank_empty_list(self):
        """Should handle empty candidate list."""
        layer = TOPSISLayer()
        hardware = create_mock_hardware()
        user_profile = create_mock_user_profile()

        ranked = layer.rank([], hardware, user_profile)

        assert ranked == []

    def test_rank_single_candidate(self):
        """Should rank single candidate."""
        layer = TOPSISLayer()
        candidates = [create_mock_candidate()]
        hardware = create_mock_hardware()
        user_profile = create_mock_user_profile()

        ranked = layer.rank(candidates, hardware, user_profile)

        assert len(ranked) == 1
        assert ranked[0].final_rank == 1

    def test_rank_multiple_candidates_sorted(self):
        """Should sort candidates by closeness coefficient."""
        layer = TOPSISLayer()
        candidates = [
            create_mock_candidate(
                model_id="high",
                similarity_score=0.9,
                speed_score=0.9,
            ),
            create_mock_candidate(
                model_id="low",
                similarity_score=0.3,
                speed_score=0.3,
            ),
        ]
        hardware = create_mock_hardware()
        user_profile = create_mock_user_profile()

        ranked = layer.rank(candidates, hardware, user_profile)

        assert len(ranked) == 2
        assert ranked[0].final_rank == 1
        assert ranked[1].final_rank == 2
        # High scorer should be first
        assert ranked[0].scored_candidate.passing_candidate.model.id == "high"

    def test_rank_assigns_sequential_ranks(self):
        """Should assign sequential ranks."""
        layer = TOPSISLayer()
        candidates = [
            create_mock_candidate(model_id="a", similarity_score=0.9),
            create_mock_candidate(model_id="b", similarity_score=0.7),
            create_mock_candidate(model_id="c", similarity_score=0.5),
        ]
        hardware = create_mock_hardware()
        user_profile = create_mock_user_profile()

        ranked = layer.rank(candidates, hardware, user_profile)

        ranks = [r.final_rank for r in ranked]
        assert ranks == [1, 2, 3]


class TestSpeedPriorityAdjustment:
    """Tests for speed priority weight adjustment."""

    def test_adjust_for_high_speed_priority(self):
        """High speed priority should increase speed_fit weight."""
        layer = TOPSISLayer()
        original_speed_weight = layer.weights["speed_fit"]

        layer.adjust_for_speed_priority(5)

        assert layer.weights["speed_fit"] > original_speed_weight

    def test_adjust_for_low_speed_priority(self):
        """Low speed priority should decrease speed_fit weight."""
        layer = TOPSISLayer()
        original_speed_weight = layer.weights["speed_fit"]

        layer.adjust_for_speed_priority(1)

        assert layer.weights["speed_fit"] < original_speed_weight

    def test_adjust_weights_still_sum_to_one(self):
        """Adjusted weights should still sum to approximately 1.0."""
        layer = TOPSISLayer()

        layer.adjust_for_speed_priority(5)
        total = sum(layer.weights.values())

        assert abs(total - 1.0) < 0.01


class TestExplanationGeneration:
    """Tests for explanation generation."""

    def test_generates_explanation_with_model_name(self):
        """Explanation should include model name."""
        layer = TOPSISLayer()
        candidate = create_mock_candidate(model_name="Super Model")
        scores = {
            "content_similarity": CriterionScore(
                criterion_id="content_similarity",
                raw_score=0.9,
                weight=0.35,
                weighted_score=0.3,
            ),
        }

        explanation = layer._generate_explanation(candidate, scores, 0.8)

        assert "Super Model" in explanation


class TestCriterionScoreDataclass:
    """Tests for CriterionScore dataclass."""

    def test_criterion_score_fields(self):
        """CriterionScore should hold all fields."""
        score = CriterionScore(
            criterion_id="hardware_fit",
            raw_score=0.8,
            weight=0.25,
            weighted_score=0.2,
            is_benefit=True,
        )
        assert score.criterion_id == "hardware_fit"
        assert score.raw_score == 0.8
        assert score.weight == 0.25
        assert score.weighted_score == 0.2
        assert score.is_benefit is True


class TestRankedCandidateDataclass:
    """Tests for RankedCandidate dataclass."""

    def test_ranked_candidate_fields(self):
        """RankedCandidate should hold all fields."""
        scored = create_mock_candidate()
        ranked = RankedCandidate(
            scored_candidate=scored,
            closeness_coefficient=0.75,
            final_rank=1,
            explanation="Top pick",
        )
        assert ranked.closeness_coefficient == 0.75
        assert ranked.final_rank == 1
        assert ranked.explanation == "Top pick"
