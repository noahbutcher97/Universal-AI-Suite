"""
Unit tests for Layer 2: Content-Based Filtering.

Tests the modular modality scoring architecture per SPEC_v3 Section 6.3.1.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Any

from src.services.recommendation.content_layer import (
    ContentBasedLayer,
    ImageScorer,
    VideoScorer,
    ModalityScorer,
    MODALITY_SCORERS,
)
from src.schemas.recommendation import (
    UseCaseDefinition,
    SharedQualityPrefs,
    ImageModalityPrefs,
    VideoModalityPrefs,
    USE_CASE_TEMPLATES,
    convert_legacy_preferences,
    ContentPreferences,
    UserProfile,
    FeatureMatch,
    ScoredCandidate,
    PassingCandidate,
)


# --- Mock ModelEntry for testing ---


@dataclass
class MockCapabilities:
    """Mock capabilities for testing."""
    scores: Dict[str, float] = field(default_factory=dict)
    style_strengths: List[str] = field(default_factory=list)


@dataclass
class MockModelVariant:
    """Mock model variant for testing."""
    id: str = "fp16"
    precision: str = "fp16"
    vram_min_mb: int = 4096
    vram_recommended_mb: int = 8192
    download_size_gb: float = 2.5


@dataclass
class MockModelEntry:
    """Mock model entry for testing."""
    id: str = "test_model"
    display_name: str = "Test Model"
    capabilities: MockCapabilities = field(default_factory=MockCapabilities)


# --- Scorer Registry Tests ---


class TestModalityScorerRegistry:
    """Tests for the modality scorer registry."""

    def test_registry_has_image_scorer(self):
        """Registry should include ImageScorer."""
        assert "image" in MODALITY_SCORERS
        assert MODALITY_SCORERS["image"] == ImageScorer

    def test_registry_has_video_scorer(self):
        """Registry should include VideoScorer."""
        assert "video" in MODALITY_SCORERS
        assert MODALITY_SCORERS["video"] == VideoScorer

    def test_all_scorers_are_modality_scorer_subclasses(self):
        """All registered scorers should be ModalityScorer subclasses."""
        for modality, scorer_class in MODALITY_SCORERS.items():
            assert issubclass(scorer_class, ModalityScorer), (
                f"{modality} scorer is not a ModalityScorer subclass"
            )


# --- ImageScorer Tests ---


class TestImageScorer:
    """Tests for the ImageScorer class."""

    def test_modality_id(self):
        """ImageScorer should return 'image' as modality_id."""
        scorer = ImageScorer()
        assert scorer.modality_id == "image"

    def test_dimension_weights_include_image_specific(self):
        """ImageScorer should have image-specific dimension weights."""
        scorer = ImageScorer()
        weights = scorer.get_dimension_weights()

        # Image-specific dimensions
        assert "editability" in weights
        assert "holistic_edits" in weights
        assert "localized_edits" in weights
        assert "pose_control" in weights

        # Shared dimensions
        assert "photorealism" in weights
        assert "output_quality" in weights

    def test_build_user_vector_from_prefs(self):
        """ImageScorer should build user vector from shared + image prefs."""
        scorer = ImageScorer()

        shared = SharedQualityPrefs(
            photorealism=5,  # Max = 1.0 normalized
            artistic_stylization=1,  # Min = 0.0 normalized
            generation_speed=3,  # Mid = 0.5 normalized
            output_quality=4,
        )
        image_prefs = ImageModalityPrefs(
            editability=5,
            pose_control=4,
        )

        vector = scorer.build_user_vector(shared, image_prefs)

        # Check normalization: (value - 1) / 4.0
        assert vector["photorealism"] == 1.0
        assert vector["artistic_stylization"] == 0.0
        assert vector["generation_speed"] == 0.5
        assert vector["editability"] == 1.0
        assert vector["pose_control"] == 0.75

    def test_build_model_vector(self):
        """ImageScorer should build model vector from capabilities."""
        scorer = ImageScorer()

        model = MockModelEntry(
            capabilities=MockCapabilities(
                scores={
                    "photorealism": 0.9,
                    "artistic_stylization": 0.7,
                    "editability": 0.8,
                    "pose_control": 0.6,
                }
            )
        )

        vector = scorer.build_model_vector(model)

        assert vector["photorealism"] == 0.9
        assert vector["artistic_stylization"] == 0.7
        assert vector["editability"] == 0.8
        assert vector["pose_control"] == 0.6

    def test_score_returns_similarity_and_matches(self):
        """ImageScorer.score() should return similarity and feature matches."""
        scorer = ImageScorer()

        model = MockModelEntry(
            capabilities=MockCapabilities(
                scores={
                    "photorealism": 0.9,
                    "artistic_stylization": 0.3,
                    "output_quality": 0.8,
                }
            )
        )

        shared = SharedQualityPrefs(
            photorealism=5,  # High priority
            artistic_stylization=1,  # Low priority
            output_quality=4,
        )

        similarity, matches = scorer.score(model, shared, None)

        # Should return a float similarity
        assert isinstance(similarity, float)
        assert 0.0 <= similarity <= 1.0

        # Should return feature matches
        assert isinstance(matches, list)


# --- VideoScorer Tests ---


class TestVideoScorer:
    """Tests for the VideoScorer class."""

    def test_modality_id(self):
        """VideoScorer should return 'video' as modality_id."""
        scorer = VideoScorer()
        assert scorer.modality_id == "video"

    def test_dimension_weights_include_video_specific(self):
        """VideoScorer should have video-specific dimension weights."""
        scorer = VideoScorer()
        weights = scorer.get_dimension_weights()

        # Video-specific dimensions
        assert "motion_intensity" in weights
        assert "temporal_coherence" in weights

        # Shared dimensions
        assert "photorealism" in weights
        assert "output_quality" in weights

    def test_build_user_vector_with_video_prefs(self):
        """VideoScorer should include video preferences in user vector."""
        scorer = VideoScorer()

        shared = SharedQualityPrefs(photorealism=3, output_quality=4)
        video_prefs = VideoModalityPrefs(
            motion_intensity=5,  # Dynamic motion
            temporal_coherence=4,
        )

        vector = scorer.build_user_vector(shared, video_prefs)

        assert vector["motion_intensity"] == 1.0  # (5-1)/4
        assert vector["temporal_coherence"] == 0.75  # (4-1)/4

    def test_build_model_vector_with_video_capabilities(self):
        """VideoScorer should extract video capabilities from model."""
        scorer = VideoScorer()

        model = MockModelEntry(
            capabilities=MockCapabilities(
                scores={
                    "photorealism": 0.8,
                    "motion_intensity": 0.9,
                    "temporal_coherence": 0.85,
                }
            )
        )

        vector = scorer.build_model_vector(model)

        assert vector["motion_intensity"] == 0.9
        assert vector["temporal_coherence"] == 0.85


# --- ContentBasedLayer Tests ---


class TestContentBasedLayer:
    """Tests for the ContentBasedLayer class."""

    def test_init_creates_scorers(self):
        """ContentBasedLayer should instantiate all registered scorers."""
        layer = ContentBasedLayer()

        assert "image" in layer._scorers
        assert "video" in layer._scorers
        assert isinstance(layer._scorers["image"], ImageScorer)
        assert isinstance(layer._scorers["video"], VideoScorer)

    def test_get_modality_prefs_extracts_image(self):
        """_get_modality_prefs should extract image preferences."""
        layer = ContentBasedLayer()

        image_prefs = ImageModalityPrefs(editability=4)
        use_case = UseCaseDefinition(
            id="test",
            name="Test",
            required_modalities=["image"],
            image=image_prefs,
        )

        result = layer._get_modality_prefs(use_case, "image")
        assert result == image_prefs

    def test_get_modality_prefs_extracts_video(self):
        """_get_modality_prefs should extract video preferences."""
        layer = ContentBasedLayer()

        video_prefs = VideoModalityPrefs(motion_intensity=5)
        use_case = UseCaseDefinition(
            id="test",
            name="Test",
            required_modalities=["video"],
            video=video_prefs,
        )

        result = layer._get_modality_prefs(use_case, "video")
        assert result == video_prefs

    def test_get_modality_prefs_returns_none_for_missing(self):
        """_get_modality_prefs should return None for missing modality."""
        layer = ContentBasedLayer()

        use_case = UseCaseDefinition(
            id="test",
            name="Test",
            required_modalities=["image"],
        )

        result = layer._get_modality_prefs(use_case, "video")
        assert result is None

    def test_score_for_use_case_single_modality(self):
        """score_for_use_case should work with single modality use cases."""
        layer = ContentBasedLayer()

        model = MockModelEntry(
            capabilities=MockCapabilities(
                scores={
                    "photorealism": 0.9,
                    "output_quality": 0.8,
                },
                style_strengths=[],
            )
        )

        candidate = PassingCandidate(
            model=model,
            variant=MockModelVariant(),
            execution_mode="native",
            warnings=[],
        )

        use_case = UseCaseDefinition(
            id="txt2img",
            name="Text to Image",
            required_modalities=["image"],
            shared=SharedQualityPrefs(photorealism=5, output_quality=4),
        )

        results = layer.score_for_use_case([candidate], use_case)

        assert len(results) == 1
        assert isinstance(results[0], ScoredCandidate)
        assert results[0].similarity_score >= 0.0
        assert results[0].similarity_score <= 1.0

    def test_score_for_use_case_multi_modality(self):
        """score_for_use_case should aggregate scores for multi-modality use cases."""
        layer = ContentBasedLayer()

        model = MockModelEntry(
            capabilities=MockCapabilities(
                scores={
                    "photorealism": 0.9,
                    "output_quality": 0.8,
                    "motion_intensity": 0.7,
                    "temporal_coherence": 0.85,
                },
                style_strengths=[],
            )
        )

        candidate = PassingCandidate(
            model=model,
            variant=MockModelVariant(),
            execution_mode="native",
            warnings=[],
        )

        use_case = UseCaseDefinition(
            id="character_animation",
            name="Character Animation",
            required_modalities=["image", "video"],
            shared=SharedQualityPrefs(photorealism=4, output_quality=5),
            image=ImageModalityPrefs(editability=3),
            video=VideoModalityPrefs(motion_intensity=4, temporal_coherence=5),
        )

        results = layer.score_for_use_case([candidate], use_case)

        assert len(results) == 1
        assert results[0].similarity_score >= 0.0
        # Multi-modal should aggregate both image and video scores

    def test_score_for_use_case_handles_missing_modality_gracefully(self):
        """score_for_use_case should handle unknown modalities gracefully."""
        layer = ContentBasedLayer()

        model = MockModelEntry(
            capabilities=MockCapabilities(
                scores={"photorealism": 0.9},
                style_strengths=[],
            )
        )

        candidate = PassingCandidate(
            model=model,
            variant=MockModelVariant(),
            execution_mode="native",
            warnings=[],
        )

        # Use case with unknown modality
        use_case = UseCaseDefinition(
            id="test_3d",
            name="Test 3D",
            required_modalities=["image", "3d"],  # "3d" not in registry yet
            shared=SharedQualityPrefs(),
        )

        # Should not raise, should fall back to available scorers
        results = layer.score_for_use_case([candidate], use_case)

        assert len(results) == 1

    def test_score_for_use_case_sorts_by_total_score(self):
        """score_for_use_case should sort candidates by total score (desc)."""
        layer = ContentBasedLayer()

        model_high = MockModelEntry(
            id="high",
            capabilities=MockCapabilities(
                scores={"photorealism": 0.95, "output_quality": 0.9},
                style_strengths=["photorealistic"],
            )
        )
        model_low = MockModelEntry(
            id="low",
            capabilities=MockCapabilities(
                scores={"photorealism": 0.3, "output_quality": 0.4},
                style_strengths=[],
            )
        )

        candidates = [
            PassingCandidate(
                model=model_low,
                variant=MockModelVariant(),
                execution_mode="native",
                warnings=[],
            ),
            PassingCandidate(
                model=model_high,
                variant=MockModelVariant(),
                execution_mode="native",
                warnings=[],
            ),
        ]

        use_case = UseCaseDefinition(
            id="txt2img",
            name="Test",
            required_modalities=["image"],
            shared=SharedQualityPrefs(photorealism=5, output_quality=5),
            image=ImageModalityPrefs(style_tags=["photorealistic"]),
        )

        results = layer.score_for_use_case(candidates, use_case)

        # High scorer should come first
        assert results[0].passing_candidate.model.id == "high"
        assert results[1].passing_candidate.model.id == "low"


# --- Legacy Score Method Tests ---


class TestContentBasedLayerLegacy:
    """Tests for backward-compatible legacy score() method."""

    def test_legacy_score_method_still_works(self):
        """Legacy score() method should still work with ContentPreferences."""
        layer = ContentBasedLayer()

        model = MockModelEntry(
            capabilities=MockCapabilities(
                scores={"photorealism": 0.9, "output_quality": 0.8},
                style_strengths=[],
            )
        )

        candidate = PassingCandidate(
            model=model,
            variant=MockModelVariant(),
            execution_mode="native",
            warnings=[],
        )

        user_profile = UserProfile(
            content_preferences={
                "txt2img": ContentPreferences(photorealism=5, output_quality=4),
            }
        )

        results = layer.score([candidate], user_profile, "txt2img")

        assert len(results) == 1
        assert results[0].similarity_score >= 0.0


# --- USE_CASE_TEMPLATES Tests ---


class TestUseCaseTemplates:
    """Tests for pre-defined use case templates."""

    def test_txt2img_template_is_image_only(self):
        """txt2img template should only require image modality."""
        template = USE_CASE_TEMPLATES["txt2img"]
        assert template.required_modalities == ["image"]

    def test_txt2vid_template_is_video_only(self):
        """txt2vid template should only require video modality."""
        template = USE_CASE_TEMPLATES["txt2vid"]
        assert template.required_modalities == ["video"]

    def test_character_animation_requires_image_and_video(self):
        """character_animation should require both image and video."""
        template = USE_CASE_TEMPLATES["character_animation"]
        assert "image" in template.required_modalities
        assert "video" in template.required_modalities


# --- Legacy Conversion Tests ---


class TestConvertLegacyPreferences:
    """Tests for convert_legacy_preferences function."""

    def test_converts_txt2img_correctly(self):
        """Should convert txt2img use case correctly."""
        legacy = ContentPreferences(
            photorealism=5,
            artistic_stylization=2,
            editability=4,
        )

        result = convert_legacy_preferences("txt2img", legacy)

        assert result.id == "txt2img"
        assert result.required_modalities == ["image"]
        assert result.shared.photorealism == 5
        assert result.image is not None
        assert result.image.editability == 4
        assert result.video is None

    def test_converts_txt2vid_correctly(self):
        """Should convert txt2vid use case correctly."""
        legacy = ContentPreferences(
            photorealism=4,
            motion_intensity=5,
            temporal_coherence=4,
        )

        result = convert_legacy_preferences("txt2vid", legacy)

        assert result.id == "txt2vid"
        assert result.required_modalities == ["video"]
        assert result.video is not None
        assert result.video.motion_intensity == 5
        assert result.video.temporal_coherence == 4
        assert result.image is None

    def test_converts_character_animation_with_both_modalities(self):
        """Should convert character_animation with both modalities."""
        legacy = ContentPreferences(
            photorealism=4,
            editability=3,
            motion_intensity=4,
            temporal_coherence=5,
        )

        result = convert_legacy_preferences("character_animation", legacy)

        assert "image" in result.required_modalities
        assert "video" in result.required_modalities
        assert result.image is not None
        assert result.video is not None
