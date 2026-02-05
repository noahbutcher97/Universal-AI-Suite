"""
Layer 2: Content-Based Filtering Layer.

Cosine similarity matching between user preferences and model capabilities
per SPEC_v3 Section 6.3.

Computes similarity scores based on:
- User's 5 aggregated factors (from onboarding)
- Model's capability vectors
- Style tag matching

SPEC_v3 Section 6.3.1 Modular Modality Architecture:
- Use cases can span multiple modalities (image+video, etc.)
- Each modality has its own scorer (ImageScorer, VideoScorer, etc.)
- Scorers aggregate via weighted average based on use case requirements
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple, Type
import math

from src.schemas.recommendation import (
    UserProfile,
    ContentPreferences,
    UseCaseDefinition,
    SharedQualityPrefs,
    ImageModalityPrefs,
    VideoModalityPrefs,
    PassingCandidate,
    FeatureMatch,
    ScoredCandidate
)
from src.schemas.model import ModelEntry


# --- Modality Scorers (SPEC_v3 Section 6.3.2) ---


class ModalityScorer(ABC):
    """
    Abstract base class for modality-specific scoring.

    Per SPEC_v3 Section 6.3.2: Each modality has its own scorer that:
    - Extracts relevant dimensions from model capabilities
    - Compares against modality-specific user preferences
    - Returns similarity score for that modality only
    """

    @property
    @abstractmethod
    def modality_id(self) -> str:
        """Return the modality identifier (e.g., 'image', 'video')."""
        pass

    @abstractmethod
    def build_user_vector(
        self,
        shared_prefs: SharedQualityPrefs,
        modality_prefs: Optional[object],
    ) -> Dict[str, float]:
        """
        Build user preference vector for this modality.

        Args:
            shared_prefs: Cross-cutting quality preferences
            modality_prefs: Modality-specific preferences (or None)

        Returns:
            Dict mapping dimension name to normalized score (0.0-1.0)
        """
        pass

    @abstractmethod
    def build_model_vector(self, model: ModelEntry) -> Dict[str, float]:
        """
        Build model capability vector for this modality.

        Args:
            model: Model entry from database

        Returns:
            Dict mapping dimension name to capability score (0.0-1.0)
        """
        pass

    @abstractmethod
    def get_dimension_weights(self) -> Dict[str, float]:
        """Return weights for each dimension in this modality."""
        pass

    def score(
        self,
        model: ModelEntry,
        shared_prefs: SharedQualityPrefs,
        modality_prefs: Optional[object],
    ) -> Tuple[float, List[FeatureMatch]]:
        """
        Compute similarity score for this modality.

        Args:
            model: Model to score
            shared_prefs: Cross-cutting quality preferences
            modality_prefs: Modality-specific preferences (or None)

        Returns:
            Tuple of (similarity_score, matching_features)
        """
        user_vector = self.build_user_vector(shared_prefs, modality_prefs)
        model_vector = self.build_model_vector(model)

        similarity = self._cosine_similarity(user_vector, model_vector)
        matches = self._identify_matches(user_vector, model_vector)

        return similarity, matches

    def _cosine_similarity(
        self,
        vec_a: Dict[str, float],
        vec_b: Dict[str, float],
    ) -> float:
        """Compute weighted cosine similarity between two vectors."""
        dimensions = set(vec_a.keys()) & set(vec_b.keys())

        if not dimensions:
            return 0.0

        weights = self.get_dimension_weights()
        dot_product = 0.0
        mag_a = 0.0
        mag_b = 0.0

        for dim in dimensions:
            weight = weights.get(dim, 1.0)
            a = vec_a[dim] * weight
            b = vec_b[dim] * weight

            dot_product += a * b
            mag_a += a * a
            mag_b += b * b

        if mag_a == 0 or mag_b == 0:
            return 0.0

        similarity = dot_product / (math.sqrt(mag_a) * math.sqrt(mag_b))
        return max(0.0, min(1.0, similarity))

    def _identify_matches(
        self,
        user_vector: Dict[str, float],
        model_vector: Dict[str, float],
    ) -> List[FeatureMatch]:
        """Identify features that contributed to the match."""
        matches = []

        for dim in user_vector:
            if dim not in model_vector:
                continue

            user_val = user_vector[dim]
            model_val = model_vector[dim]
            contribution = user_val * model_val

            # Per SPEC_v3: Only include significant contributions
            CONTRIBUTION_THRESHOLD = 0.1
            if contribution > CONTRIBUTION_THRESHOLD:
                matches.append(FeatureMatch(
                    feature_id=dim,
                    user_value=user_val,
                    model_value=model_val,
                    contribution=contribution,
                ))

        matches.sort(key=lambda m: m.contribution, reverse=True)
        return matches[:5]


class ImageScorer(ModalityScorer):
    """
    Scorer for image generation modality.

    Per SPEC_v3 Section 6.3.1: Image-specific dimensions include
    editability, pose control, holistic/localized edits, style matching.
    """

    # Dimension weights for image modality
    # Per SPEC_v3: Quality dimensions weighted higher for image
    IMAGE_DIMENSION_WEIGHTS = {
        "photorealism": 1.0,
        "artistic_stylization": 1.0,
        "generation_speed": 0.8,
        "output_quality": 0.9,
        "editability": 0.7,
        "holistic_edits": 0.6,
        "localized_edits": 0.6,
        "pose_control": 0.7,
        "character_consistency": 0.8,
    }

    @property
    def modality_id(self) -> str:
        return "image"

    def get_dimension_weights(self) -> Dict[str, float]:
        return self.IMAGE_DIMENSION_WEIGHTS

    def build_user_vector(
        self,
        shared_prefs: SharedQualityPrefs,
        modality_prefs: Optional[ImageModalityPrefs],
    ) -> Dict[str, float]:
        """Build user vector from shared + image preferences."""
        # Normalize 1-5 scale to 0.0-1.0
        # Per SPEC_v3: (value - 1) / 4.0 for 1-5 scale normalization
        SCALE_DIVISOR = 4.0
        SCALE_OFFSET = 1

        vector = {
            "photorealism": (shared_prefs.photorealism - SCALE_OFFSET) / SCALE_DIVISOR,
            "artistic_stylization": (shared_prefs.artistic_stylization - SCALE_OFFSET) / SCALE_DIVISOR,
            "generation_speed": (shared_prefs.generation_speed - SCALE_OFFSET) / SCALE_DIVISOR,
            "output_quality": (shared_prefs.output_quality - SCALE_OFFSET) / SCALE_DIVISOR,
        }

        # Character consistency from shared (used across modalities)
        if shared_prefs.character_consistency is not None:
            vector["character_consistency"] = (
                shared_prefs.character_consistency - SCALE_OFFSET
            ) / SCALE_DIVISOR

        # Image-specific preferences
        if modality_prefs is not None:
            vector["editability"] = (modality_prefs.editability - SCALE_OFFSET) / SCALE_DIVISOR

            if modality_prefs.pose_control is not None:
                vector["pose_control"] = (
                    modality_prefs.pose_control - SCALE_OFFSET
                ) / SCALE_DIVISOR

            if modality_prefs.holistic_edits is not None:
                vector["holistic_edits"] = (
                    modality_prefs.holistic_edits - SCALE_OFFSET
                ) / SCALE_DIVISOR

            if modality_prefs.localized_edits is not None:
                vector["localized_edits"] = (
                    modality_prefs.localized_edits - SCALE_OFFSET
                ) / SCALE_DIVISOR

        return vector

    def build_model_vector(self, model: ModelEntry) -> Dict[str, float]:
        """Build model capability vector for image modality."""
        scores = model.capabilities.scores

        vector = {
            "photorealism": scores.get("photorealism", 0.5),
            "artistic_stylization": scores.get(
                "artistic_stylization",
                scores.get("artistic_quality", 0.5)
            ),
            "generation_speed": scores.get(
                "generation_speed",
                scores.get("speed", 0.5)
            ),
            "output_quality": scores.get(
                "output_quality",
                scores.get("output_fidelity", 0.5)
            ),
            "editability": scores.get("editability", 0.0),
        }

        # Optional capabilities
        if scores.get("character_consistency", 0.0) > 0:
            vector["character_consistency"] = scores["character_consistency"]

        if scores.get("pose_control", 0.0) > 0:
            vector["pose_control"] = scores["pose_control"]

        if scores.get("holistic_editing", 0.0) > 0:
            vector["holistic_edits"] = scores["holistic_editing"]

        if scores.get("localized_editing", 0.0) > 0:
            vector["localized_edits"] = scores["localized_editing"]

        return vector


class VideoScorer(ModalityScorer):
    """
    Scorer for video generation modality.

    Per SPEC_v3 Section 6.3.1: Video-specific dimensions include
    motion intensity, temporal coherence, character consistency.
    """

    # Dimension weights for video modality
    # Per SPEC_v3: Motion and temporal dimensions weighted higher for video
    VIDEO_DIMENSION_WEIGHTS = {
        "photorealism": 0.8,
        "artistic_stylization": 0.8,
        "generation_speed": 0.9,
        "output_quality": 0.9,
        "motion_intensity": 1.0,
        "temporal_coherence": 1.0,
        "character_consistency": 0.9,
    }

    @property
    def modality_id(self) -> str:
        return "video"

    def get_dimension_weights(self) -> Dict[str, float]:
        return self.VIDEO_DIMENSION_WEIGHTS

    def build_user_vector(
        self,
        shared_prefs: SharedQualityPrefs,
        modality_prefs: Optional[VideoModalityPrefs],
    ) -> Dict[str, float]:
        """Build user vector from shared + video preferences."""
        # Per SPEC_v3: (value - 1) / 4.0 for 1-5 scale normalization
        SCALE_DIVISOR = 4.0
        SCALE_OFFSET = 1

        vector = {
            "photorealism": (shared_prefs.photorealism - SCALE_OFFSET) / SCALE_DIVISOR,
            "artistic_stylization": (shared_prefs.artistic_stylization - SCALE_OFFSET) / SCALE_DIVISOR,
            "generation_speed": (shared_prefs.generation_speed - SCALE_OFFSET) / SCALE_DIVISOR,
            "output_quality": (shared_prefs.output_quality - SCALE_OFFSET) / SCALE_DIVISOR,
        }

        # Character consistency from shared (critical for video)
        if shared_prefs.character_consistency is not None:
            vector["character_consistency"] = (
                shared_prefs.character_consistency - SCALE_OFFSET
            ) / SCALE_DIVISOR

        # Video-specific preferences
        if modality_prefs is not None:
            vector["motion_intensity"] = (
                modality_prefs.motion_intensity - SCALE_OFFSET
            ) / SCALE_DIVISOR
            vector["temporal_coherence"] = (
                modality_prefs.temporal_coherence - SCALE_OFFSET
            ) / SCALE_DIVISOR

        return vector

    def build_model_vector(self, model: ModelEntry) -> Dict[str, float]:
        """Build model capability vector for video modality."""
        scores = model.capabilities.scores

        vector = {
            "photorealism": scores.get("photorealism", 0.5),
            "artistic_stylization": scores.get(
                "artistic_stylization",
                scores.get("artistic_quality", 0.5)
            ),
            "generation_speed": scores.get(
                "generation_speed",
                scores.get("speed", 0.5)
            ),
            "output_quality": scores.get(
                "output_quality",
                scores.get("output_fidelity", 0.5)
            ),
        }

        # Video-specific: Motion intensity
        motion = scores.get(
            "motion_intensity",
            scores.get("motion_quality", scores.get("motion_dynamic", 0.0))
        )
        if motion > 0:
            vector["motion_intensity"] = motion

        # Video-specific: Temporal coherence
        temporal = scores.get("temporal_coherence", 0.0)
        if temporal > 0:
            vector["temporal_coherence"] = temporal

        # Character consistency
        if scores.get("character_consistency", 0.0) > 0:
            vector["character_consistency"] = scores["character_consistency"]

        return vector


# --- Scorer Registry ---

MODALITY_SCORERS: Dict[str, Type[ModalityScorer]] = {
    "image": ImageScorer,
    "video": VideoScorer,
    # Future: "audio": AudioScorer, "3d": ThreeDScorer
}


class ContentBasedLayer:
    """
    Layer 2: Content-Based Filtering.

    Computes cosine similarity between user preference vectors and model
    capability vectors. Returns candidates ranked by similarity.

    SPEC_v3 Section 6.3:
    - User vector: 5 aggregated factors from onboarding
    - Model vector: Capability scores from models_database.yaml
    - Similarity: cosine(user_vector, model_vector)
    - Bonus: Style tag matches

    SPEC_v3 Section 6.3.1 Modular Architecture:
    - Use cases can span multiple modalities
    - score_for_use_case() uses modality-specific scorers
    - Scores are aggregated via weighted average
    """

    # Weights for different capability dimensions (legacy, for backward compat)
    # Aligned with ContentPreferences schema field names
    DIMENSION_WEIGHTS = {
        "photorealism": 1.0,
        "artistic_stylization": 1.0,
        "generation_speed": 0.8,
        "output_quality": 0.9,
        "consistency": 0.7,
        "editability": 0.6,
        "motion_intensity": 1.0,
        "temporal_coherence": 0.9,
    }

    # Style tag match bonus (per matching tag, capped)
    STYLE_TAG_BONUS = 0.05
    STYLE_TAG_MAX_BONUS = 0.20

    def __init__(self):
        """Initialize the content layer with modality scorers."""
        # Instantiate scorers from registry
        self._scorers: Dict[str, ModalityScorer] = {
            modality: scorer_class()
            for modality, scorer_class in MODALITY_SCORERS.items()
        }

    def score(
        self,
        candidates: List[PassingCandidate],
        user_profile: UserProfile,
        use_case: str,
    ) -> List[ScoredCandidate]:
        """
        Score candidates by similarity to user preferences.

        Args:
            candidates: Candidates that passed constraint satisfaction
            user_profile: User's preferences from onboarding
            use_case: The primary use case being evaluated

        Returns:
            List of ScoredCandidate, sorted by similarity (highest first)
        """
        # Get user's content preferences for this use case
        content_prefs = user_profile.content_preferences.get(use_case)
        if content_prefs is None:
            content_prefs = ContentPreferences()  # Default preferences

        # Build user feature vector
        user_vector = self._build_user_vector(content_prefs)

        scored = []
        for candidate in candidates:
            # Build model feature vector
            model_vector = self._build_model_vector(candidate.model)

            # Compute cosine similarity
            similarity = self._cosine_similarity(user_vector, model_vector)

            # Compute style tag bonus
            style_bonus = self._compute_style_bonus(
                content_prefs.style_tags,
                candidate.model.capabilities.style_strengths,
            )

            # Identify matching features for explainability
            matching_features = self._identify_matches(
                user_vector, model_vector, candidate.model
            )

            scored.append(ScoredCandidate(
                passing_candidate=candidate,
                similarity_score=similarity,
                matching_features=matching_features,
                style_match_bonus=style_bonus,
            ))

        # Sort by total score (similarity + bonus)
        scored.sort(
            key=lambda s: s.similarity_score + s.style_match_bonus,
            reverse=True
        )

        return scored

    def score_for_use_case(
        self,
        candidates: List[PassingCandidate],
        use_case: UseCaseDefinition,
    ) -> List[ScoredCandidate]:
        """
        Score candidates using modular modality scorers.

        Per SPEC_v3 Section 6.3.1: Use cases can span multiple modalities.
        This method:
        1. Identifies required modalities from the use case
        2. Scores each candidate with the appropriate modality scorer(s)
        3. Aggregates scores via weighted average

        Args:
            candidates: Candidates that passed constraint satisfaction
            use_case: UseCaseDefinition with modality-specific preferences

        Returns:
            List of ScoredCandidate, sorted by similarity (highest first)
        """
        if not use_case.required_modalities:
            # Fallback to single image modality if none specified
            modalities = ["image"]
        else:
            modalities = use_case.required_modalities

        # Validate we have scorers for all required modalities
        missing = [m for m in modalities if m not in self._scorers]
        if missing:
            # Log warning but continue with available scorers
            modalities = [m for m in modalities if m in self._scorers]
            if not modalities:
                # No valid modalities, return empty scores
                return [
                    ScoredCandidate(
                        passing_candidate=c,
                        similarity_score=0.0,
                    )
                    for c in candidates
                ]

        scored = []
        for candidate in candidates:
            # Score each modality
            modality_scores: Dict[str, Tuple[float, List[FeatureMatch]]] = {}

            for modality in modalities:
                scorer = self._scorers[modality]
                modality_prefs = self._get_modality_prefs(use_case, modality)

                score, matches = scorer.score(
                    model=candidate.model,
                    shared_prefs=use_case.shared,
                    modality_prefs=modality_prefs,
                )
                modality_scores[modality] = (score, matches)

            # Aggregate scores (equal weight per modality for now)
            # Per SPEC_v3: Future enhancement could use modality importance weights
            if modality_scores:
                total_score = sum(s for s, _ in modality_scores.values())
                avg_score = total_score / len(modality_scores)
            else:
                avg_score = 0.0

            # Combine all feature matches
            all_matches = []
            for _, (_, matches) in modality_scores.items():
                all_matches.extend(matches)
            all_matches.sort(key=lambda m: m.contribution, reverse=True)

            # Compute style bonus (from image modality preferences)
            style_bonus = 0.0
            if use_case.image and use_case.image.style_tags:
                style_bonus = self._compute_style_bonus(
                    use_case.image.style_tags,
                    candidate.model.capabilities.style_strengths,
                )

            scored.append(ScoredCandidate(
                passing_candidate=candidate,
                similarity_score=avg_score,
                matching_features=all_matches[:5],  # Top 5 across all modalities
                style_match_bonus=style_bonus,
            ))

        # Sort by total score
        scored.sort(
            key=lambda s: s.similarity_score + s.style_match_bonus,
            reverse=True,
        )

        return scored

    def _get_modality_prefs(
        self,
        use_case: UseCaseDefinition,
        modality: str,
    ) -> Optional[object]:
        """
        Extract modality-specific preferences from a UseCaseDefinition.

        Args:
            use_case: The use case definition
            modality: The modality to get preferences for

        Returns:
            The modality-specific preferences object, or None
        """
        modality_map = {
            "image": use_case.image,
            "video": use_case.video,
            "audio": use_case.audio,
            "3d": use_case.three_d,
        }
        return modality_map.get(modality)

    def _build_user_vector(self, prefs: ContentPreferences) -> Dict[str, float]:
        """
        Build normalized user preference vector.

        Maps 1-5 scale preferences to 0.0-1.0 scores.
        Aligned with ContentPreferences schema fields.
        """
        vector = {
            # Core preferences (always present)
            "photorealism": (prefs.photorealism - 1) / 4.0,
            "artistic_stylization": (prefs.artistic_stylization - 1) / 4.0,
            "generation_speed": (prefs.generation_speed - 1) / 4.0,
            "output_quality": (prefs.output_quality - 1) / 4.0,
            "consistency": (prefs.consistency - 1) / 4.0,
            "editability": (prefs.editability - 1) / 4.0,
        }

        # Domain-specific preferences (video/animation)
        # Only include if user has set them (non-None)
        if prefs.motion_intensity is not None:
            vector["motion_intensity"] = (prefs.motion_intensity - 1) / 4.0
        if prefs.temporal_coherence is not None:
            vector["temporal_coherence"] = (prefs.temporal_coherence - 1) / 4.0
        if prefs.character_consistency is not None:
            vector["character_consistency"] = (prefs.character_consistency - 1) / 4.0
        if prefs.pose_control is not None:
            vector["pose_control"] = (prefs.pose_control - 1) / 4.0

        return vector

    def _build_model_vector(self, model: ModelEntry) -> Dict[str, float]:
        """
        Build model capability vector from model entry.

        Uses scores from models_database.yaml capabilities.scores.
        Aligned with ContentPreferences schema fields.
        """
        scores = model.capabilities.scores

        # Build vector with aligned dimension names
        vector = {
            # Core capabilities
            "photorealism": scores.get("photorealism", 0.5),
            "artistic_stylization": scores.get("artistic_stylization",
                                               scores.get("artistic_quality", 0.5)),
            "generation_speed": scores.get("generation_speed",
                                           scores.get("speed", 0.5)),
            "output_quality": scores.get("output_quality",
                                         scores.get("output_fidelity", 0.5)),
            "consistency": scores.get("consistency", 0.5),
            "editability": scores.get("editability", 0.0),
        }

        # Domain-specific capabilities (video/animation)
        # Only include if model has these capabilities (non-zero)
        motion = scores.get("motion_intensity",
                           scores.get("motion_quality",
                                      scores.get("motion_dynamic", 0.0)))
        if motion > 0:
            vector["motion_intensity"] = motion

        temporal = scores.get("temporal_coherence", 0.0)
        if temporal > 0:
            vector["temporal_coherence"] = temporal

        char_consistency = scores.get("character_consistency", 0.0)
        if char_consistency > 0:
            vector["character_consistency"] = char_consistency

        pose = scores.get("pose_control", 0.0)
        if pose > 0:
            vector["pose_control"] = pose

        return vector

    def _cosine_similarity(
        self,
        vec_a: Dict[str, float],
        vec_b: Dict[str, float],
    ) -> float:
        """
        Compute cosine similarity between two vectors.

        Returns value between 0.0 and 1.0.
        """
        # Get common dimensions
        dimensions = set(vec_a.keys()) & set(vec_b.keys())

        if not dimensions:
            return 0.0

        # Compute dot product and magnitudes
        dot_product = 0.0
        mag_a = 0.0
        mag_b = 0.0

        for dim in dimensions:
            weight = self.DIMENSION_WEIGHTS.get(dim, 1.0)
            a = vec_a[dim] * weight
            b = vec_b[dim] * weight

            dot_product += a * b
            mag_a += a * a
            mag_b += b * b

        # Avoid division by zero
        if mag_a == 0 or mag_b == 0:
            return 0.0

        similarity = dot_product / (math.sqrt(mag_a) * math.sqrt(mag_b))

        # Clamp to [0, 1]
        return max(0.0, min(1.0, similarity))

    def _compute_style_bonus(
        self,
        user_styles: List[str],
        model_styles: List[str],
    ) -> float:
        """
        Compute bonus for matching style tags.

        Each matching tag adds STYLE_TAG_BONUS, up to STYLE_TAG_MAX_BONUS.
        """
        if not user_styles or not model_styles:
            return 0.0

        user_set = set(s.lower() for s in user_styles)
        model_set = set(s.lower() for s in model_styles)

        matches = len(user_set & model_set)
        bonus = matches * self.STYLE_TAG_BONUS

        return min(bonus, self.STYLE_TAG_MAX_BONUS)

    def _identify_matches(
        self,
        user_vector: Dict[str, float],
        model_vector: Dict[str, float],
        model: ModelEntry,
    ) -> List[FeatureMatch]:
        """
        Identify which features contributed most to the match.

        Used for explainability in recommendations.
        """
        matches = []

        for dim in user_vector:
            if dim not in model_vector:
                continue

            user_val = user_vector[dim]
            model_val = model_vector[dim]

            # Compute contribution (simplified)
            contribution = user_val * model_val

            if contribution > 0.1:  # Only significant contributions
                matches.append(FeatureMatch(
                    feature_id=dim,
                    user_value=user_val,
                    model_value=model_val,
                    contribution=contribution,
                ))

        # Sort by contribution
        matches.sort(key=lambda m: m.contribution, reverse=True)

        return matches[:5]  # Top 5 matches
