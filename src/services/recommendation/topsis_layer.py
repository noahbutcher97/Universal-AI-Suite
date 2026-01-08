"""
Layer 3: TOPSIS Multi-Criteria Ranking Layer.

Technique for Order of Preference by Similarity to Ideal Solution.
Per SPEC_v3 Section 6.4.

Criteria:
1. content_similarity - From Layer 2
2. hardware_fit - VRAM margin, form factor penalty
3. speed_fit - Storage tier, model speed scores
4. ecosystem_maturity - Community support, node availability
5. approach_fit - User's preferred complexity level
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

from src.schemas.hardware import HardwareProfile, StorageTier
from src.schemas.recommendation import UserProfile, ContentPreferences
from src.services.recommendation.content_layer import ScoredCandidate


@dataclass
class CriterionScore:
    """Score for a single TOPSIS criterion."""
    criterion_id: str
    raw_score: float  # 0.0 - 1.0
    weight: float
    weighted_score: float
    is_benefit: bool = True  # True = higher is better


@dataclass
class RankedCandidate:
    """Final ranked candidate with TOPSIS score."""
    scored_candidate: ScoredCandidate
    closeness_coefficient: float  # 0.0 - 1.0 (higher = better)
    criterion_scores: Dict[str, CriterionScore] = field(default_factory=dict)
    final_rank: int = 0
    explanation: str = ""


class TOPSISLayer:
    """
    Layer 3: TOPSIS Multi-Criteria Ranking.

    Ranks candidates using the TOPSIS algorithm with 5 criteria.
    Produces a closeness coefficient (0-1) for each candidate.

    SPEC_v3 Section 6.4:
    1. Build decision matrix (candidates x criteria)
    2. Normalize the matrix
    3. Apply criterion weights
    4. Determine ideal and anti-ideal solutions
    5. Calculate distance to ideal/anti-ideal
    6. Compute closeness coefficient

    Criteria Weights (default, can be adjusted):
    - content_similarity: 0.35
    - hardware_fit: 0.25
    - speed_fit: 0.15
    - ecosystem_maturity: 0.15
    - approach_fit: 0.10
    """

    DEFAULT_WEIGHTS = {
        "content_similarity": 0.35,
        "hardware_fit": 0.25,
        "speed_fit": 0.15,
        "ecosystem_maturity": 0.15,
        "approach_fit": 0.10,
    }

    # Form factor performance penalty
    LAPTOP_PENALTY = 0.15

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize TOPSIS layer.

        Args:
            weights: Custom criterion weights (must sum to 1.0)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

    def rank(
        self,
        candidates: List[ScoredCandidate],
        hardware: HardwareProfile,
        user_profile: UserProfile,
    ) -> List[RankedCandidate]:
        """
        Rank candidates using TOPSIS algorithm.

        Args:
            candidates: Candidates scored by content similarity
            hardware: User's hardware profile
            user_profile: User's preferences

        Returns:
            List of RankedCandidate sorted by closeness coefficient
        """
        if not candidates:
            return []

        # TODO: Implement full TOPSIS algorithm in Phase 3
        # Stub implementation

        # Step 1: Build decision matrix
        decision_matrix = self._build_decision_matrix(
            candidates, hardware, user_profile
        )

        # Step 2: Normalize the matrix
        normalized = self._normalize_matrix(decision_matrix)

        # Step 3: Apply weights
        weighted = self._apply_weights(normalized)

        # Step 4-6: Compute closeness coefficients
        ranked = self._compute_closeness(candidates, weighted)

        # Sort by closeness (descending)
        ranked.sort(key=lambda r: r.closeness_coefficient, reverse=True)

        # Assign ranks
        for i, r in enumerate(ranked):
            r.final_rank = i + 1

        return ranked

    def _build_decision_matrix(
        self,
        candidates: List[ScoredCandidate],
        hardware: HardwareProfile,
        user_profile: UserProfile,
    ) -> List[Dict[str, float]]:
        """
        Build decision matrix with scores for each criterion.

        Returns list of dicts, one per candidate.
        """
        matrix = []

        for candidate in candidates:
            scores = {
                "content_similarity": self._score_content_similarity(candidate),
                "hardware_fit": self._score_hardware_fit(candidate, hardware),
                "speed_fit": self._score_speed_fit(candidate, hardware, user_profile),
                "ecosystem_maturity": self._score_ecosystem_maturity(candidate),
                "approach_fit": self._score_approach_fit(candidate, user_profile),
            }
            matrix.append(scores)

        return matrix

    def _score_content_similarity(self, candidate: ScoredCandidate) -> float:
        """Get content similarity score from Layer 2."""
        return candidate.similarity_score + candidate.style_match_bonus

    def _score_hardware_fit(
        self,
        candidate: ScoredCandidate,
        hardware: HardwareProfile,
    ) -> float:
        """
        Score how well the model fits the hardware.

        Considers:
        - VRAM margin (headroom above minimum)
        - Form factor penalty (laptop throttling)
        """
        variant = candidate.passing_candidate.variant
        vram_mb = int(hardware.vram_gb * 1024)

        # VRAM margin score
        vram_min = variant.vram_min_mb
        vram_recommended = variant.vram_recommended_mb

        if vram_mb >= vram_recommended:
            vram_score = 1.0
        elif vram_mb >= vram_min:
            # Linear interpolation between min and recommended
            vram_score = 0.5 + 0.5 * (vram_mb - vram_min) / (vram_recommended - vram_min)
        else:
            vram_score = 0.0

        # Form factor penalty
        form_factor_penalty = 0.0
        if hardware.form_factor and hardware.form_factor.is_laptop:
            form_factor_penalty = self.LAPTOP_PENALTY
            # Reduce penalty if sustained performance is good
            if hardware.form_factor.sustained_performance_ratio > 0.7:
                form_factor_penalty *= 0.5

        return max(0.0, vram_score - form_factor_penalty)

    def _score_speed_fit(
        self,
        candidate: ScoredCandidate,
        hardware: HardwareProfile,
        user_profile: UserProfile,
    ) -> float:
        """
        Score speed characteristics.

        Considers:
        - Model speed score
        - Storage tier (affects load times)
        - User's speed priority
        """
        model = candidate.passing_candidate.model
        speed_score = model.capabilities.scores.get("speed", 0.5)

        # Storage tier adjustment
        storage_penalty = 0.0
        if hardware.storage:
            if hardware.storage.tier == StorageTier.SLOW:
                storage_penalty = 0.2
            elif hardware.storage.tier == StorageTier.MODERATE:
                storage_penalty = 0.1

        # User speed priority adjustment
        # Get the first use case's content preferences, or default
        speed_priority = 3  # Default middle priority
        if user_profile.primary_use_cases and user_profile.content_preferences:
            first_use_case = list(user_profile.primary_use_cases)[0]
            content_prefs = user_profile.content_preferences.get(first_use_case)
            if content_prefs is not None:
                speed_priority = content_prefs.generation_speed

        # If user prioritizes speed, penalize slow models more
        if speed_priority >= 4:
            speed_score = speed_score ** 0.8  # Boost fast models
        elif speed_priority <= 2:
            speed_score = speed_score ** 1.2  # Penalize slow models less

        return max(0.0, speed_score - storage_penalty)

    def _score_ecosystem_maturity(self, candidate: ScoredCandidate) -> float:
        """
        Score ecosystem maturity and community support.

        Based on:
        - Required nodes availability
        - Model family maturity
        - Cloud availability as backup
        """
        model = candidate.passing_candidate.model

        # Start with base score
        score = 0.5

        # Popular families get bonus
        mature_families = ["flux", "sdxl", "sd15", "wan", "animatediff"]
        if model.family.lower() in mature_families:
            score += 0.2

        # Fewer required nodes = more mature
        req_nodes = len(model.dependencies.required_nodes)
        if req_nodes == 0:
            score += 0.2
        elif req_nodes == 1:
            score += 0.1

        # Cloud backup available
        if model.cloud.partner_node or model.cloud.replicate:
            score += 0.1

        return min(1.0, score)

    def _score_approach_fit(
        self,
        candidate: ScoredCandidate,
        user_profile: UserProfile,
    ) -> float:
        """
        Score how well model fits user's preferred approach.

        Based on:
        - User's technical experience
        - User's prefer_simple_setup setting
        - Model complexity (nodes, dependencies)
        """
        model = candidate.passing_candidate.model

        # Determine model complexity
        node_count = len(model.dependencies.required_nodes)
        has_paired = len(model.dependencies.paired_models) > 0

        complexity_score = 0.0
        if node_count == 0 and not has_paired:
            complexity_score = 1.0  # Simple
        elif node_count <= 2 and not has_paired:
            complexity_score = 0.7  # Moderate
        else:
            complexity_score = 0.4  # Complex

        # Adjust based on user preference
        prefer_simple = user_profile.prefer_simple_setup  # 1-5
        technical_exp = user_profile.technical_experience  # 1-5

        if prefer_simple >= 4:
            # User wants simple - penalize complex models
            return complexity_score
        elif technical_exp >= 4:
            # Expert user - slightly prefer complex models (more capability)
            return 1.0 - (complexity_score * 0.3)
        else:
            # Balanced
            return 0.5 + (complexity_score * 0.3)

    def _normalize_matrix(
        self,
        matrix: List[Dict[str, float]],
    ) -> List[Dict[str, float]]:
        """
        Normalize decision matrix using vector normalization.

        For each criterion: x_norm = x / sqrt(sum(x^2))
        """
        if not matrix:
            return []

        # Compute sum of squares for each criterion
        criteria = matrix[0].keys()
        sum_squares = {c: 0.0 for c in criteria}

        for row in matrix:
            for c in criteria:
                sum_squares[c] += row[c] ** 2

        # Normalize
        normalized = []
        for row in matrix:
            norm_row = {}
            for c in criteria:
                divisor = math.sqrt(sum_squares[c]) if sum_squares[c] > 0 else 1.0
                norm_row[c] = row[c] / divisor
            normalized.append(norm_row)

        return normalized

    def _apply_weights(
        self,
        normalized: List[Dict[str, float]],
    ) -> List[Dict[str, float]]:
        """Apply criterion weights to normalized matrix."""
        weighted = []
        for row in normalized:
            weighted_row = {
                c: row[c] * self.weights.get(c, 0.0)
                for c in row
            }
            weighted.append(weighted_row)
        return weighted

    def _compute_closeness(
        self,
        candidates: List[ScoredCandidate],
        weighted: List[Dict[str, float]],
    ) -> List[RankedCandidate]:
        """
        Compute closeness coefficient for each candidate.

        C = D- / (D+ + D-)
        Where:
        - D+ = distance to ideal solution
        - D- = distance to anti-ideal solution
        """
        if not weighted:
            return []

        criteria = weighted[0].keys()

        # Find ideal (max) and anti-ideal (min) for each criterion
        # All criteria are benefit criteria (higher = better)
        ideal = {c: max(row[c] for row in weighted) for c in criteria}
        anti_ideal = {c: min(row[c] for row in weighted) for c in criteria}

        ranked = []
        for i, (candidate, row) in enumerate(zip(candidates, weighted)):
            # Distance to ideal
            d_plus = math.sqrt(sum((row[c] - ideal[c]) ** 2 for c in criteria))

            # Distance to anti-ideal
            d_minus = math.sqrt(sum((row[c] - anti_ideal[c]) ** 2 for c in criteria))

            # Closeness coefficient
            if d_plus + d_minus == 0:
                closeness = 0.5
            else:
                closeness = d_minus / (d_plus + d_minus)

            # Build criterion scores for explainability
            criterion_scores = {}
            for c in criteria:
                criterion_scores[c] = CriterionScore(
                    criterion_id=c,
                    raw_score=row[c] / self.weights.get(c, 1.0) if self.weights.get(c, 0) > 0 else 0,
                    weight=self.weights.get(c, 0.0),
                    weighted_score=row[c],
                    is_benefit=True,
                )

            # Generate explanation
            explanation = self._generate_explanation(candidate, criterion_scores, closeness)

            ranked.append(RankedCandidate(
                scored_candidate=candidate,
                closeness_coefficient=closeness,
                criterion_scores=criterion_scores,
                explanation=explanation,
            ))

        return ranked

    def _generate_explanation(
        self,
        candidate: ScoredCandidate,
        scores: Dict[str, CriterionScore],
        closeness: float,
    ) -> str:
        """Generate human-readable explanation for ranking."""
        model = candidate.passing_candidate.model

        # Find top contributing criterion
        top_criteria = sorted(
            scores.values(),
            key=lambda s: s.weighted_score,
            reverse=True
        )[:2]

        parts = [f"{model.name}"]

        for cs in top_criteria:
            criterion_name = cs.criterion_id.replace("_", " ").title()
            if cs.weighted_score > 0.15:
                parts.append(f"strong {criterion_name.lower()}")

        return " - ".join(parts[:3])

    def adjust_for_speed_priority(
        self,
        speed_priority: int,  # 1-5
    ) -> None:
        """
        Adjust weights based on user's speed priority.

        Higher speed priority = more weight on speed_fit criterion.
        """
        if speed_priority >= 4:
            # Increase speed_fit, decrease others proportionally
            self.weights["speed_fit"] = 0.25
            self.weights["content_similarity"] = 0.30
            self.weights["hardware_fit"] = 0.20
            self.weights["ecosystem_maturity"] = 0.15
            self.weights["approach_fit"] = 0.10
        elif speed_priority <= 2:
            # Decrease speed_fit
            self.weights["speed_fit"] = 0.10
            self.weights["content_similarity"] = 0.40
            self.weights["hardware_fit"] = 0.25
            self.weights["ecosystem_maturity"] = 0.15
            self.weights["approach_fit"] = 0.10
