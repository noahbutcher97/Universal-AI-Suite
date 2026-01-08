"""
Recommendation Explainer.

Generates human-readable explanations for recommendation decisions.
Supports transparency and user trust by explaining:
- Why a model was recommended
- Why a model was rejected
- What trade-offs were made
- How to improve results (hardware upgrades, etc.)

Per SPEC_v3 Section 6.6 (Explainability).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from src.schemas.hardware import HardwareProfile, PlatformType, CPUTier, StorageTier
from src.services.recommendation.constraint_layer import (
    PassingCandidate,
    RejectedCandidate,
    RejectionReason,
)
from src.services.recommendation.content_layer import ScoredCandidate, FeatureMatch
from src.services.recommendation.topsis_layer import RankedCandidate, CriterionScore


class ExplanationType(Enum):
    """Types of explanations."""
    RECOMMENDATION = "recommendation"
    REJECTION = "rejection"
    TRADE_OFF = "trade_off"
    IMPROVEMENT = "improvement"
    WARNING = "warning"


@dataclass
class ExplanationItem:
    """A single explanation item."""
    type: ExplanationType
    title: str
    description: str
    details: Optional[str] = None
    priority: int = 0  # Higher = more important


@dataclass
class ModelExplanation:
    """Complete explanation for a model recommendation."""
    model_id: str
    model_name: str
    rank: int
    score: float  # 0.0 - 1.0
    items: List[ExplanationItem] = field(default_factory=list)
    summary: str = ""
    is_recommended: bool = True


@dataclass
class RecommendationReport:
    """Full explanation report for all recommendations."""
    primary_recommendation: Optional[ModelExplanation] = None
    alternatives: List[ModelExplanation] = field(default_factory=list)
    rejected_models: List[ModelExplanation] = field(default_factory=list)
    hardware_summary: str = ""
    improvement_suggestions: List[ExplanationItem] = field(default_factory=list)


class RecommendationExplainer:
    """
    Generates explanations for recommendation decisions.

    Produces human-readable text explaining:
    1. Why the top model was chosen
    2. Key trade-offs made
    3. Why other models were rejected
    4. How hardware upgrades could improve options
    """

    # Friendly names for rejection reasons
    REJECTION_MESSAGES = {
        RejectionReason.INSUFFICIENT_VRAM: "Not enough GPU memory (VRAM)",
        RejectionReason.PLATFORM_INCOMPATIBLE: "Not compatible with your operating system",
        RejectionReason.COMPUTE_CAPABILITY_TOO_LOW: "GPU compute capability too low",
        RejectionReason.EXCLUDED_BY_USER: "Excluded by your preferences",
        RejectionReason.INSUFFICIENT_STORAGE: "Not enough disk space",
        RejectionReason.MPS_KQUANT_CRASH: "This quantization format crashes on Apple Silicon",
        RejectionReason.APPLE_SILICON_EXCLUDED: "Performance too slow on Apple Silicon",
    }

    # Friendly names for TOPSIS criteria
    CRITERION_NAMES = {
        "content_similarity": "Match with Your Preferences",
        "hardware_fit": "Hardware Compatibility",
        "speed_fit": "Generation Speed",
        "ecosystem_maturity": "Community Support",
        "approach_fit": "Ease of Use",
    }

    def __init__(self):
        """Initialize explainer."""
        pass

    def explain_recommendations(
        self,
        ranked: List[RankedCandidate],
        rejected: List[RejectedCandidate],
        hardware: HardwareProfile,
        use_case: str,
    ) -> RecommendationReport:
        """
        Generate complete explanation report.

        Args:
            ranked: Ranked candidates from TOPSIS layer
            rejected: Rejected candidates from constraint layer
            hardware: User's hardware profile
            use_case: The use case being evaluated

        Returns:
            RecommendationReport with full explanations
        """
        report = RecommendationReport()

        # Hardware summary
        report.hardware_summary = self._summarize_hardware(hardware)

        # Explain primary recommendation
        if ranked:
            report.primary_recommendation = self._explain_ranked_model(
                ranked[0], rank=1, is_primary=True
            )

            # Alternatives (positions 2-5)
            for i, candidate in enumerate(ranked[1:5], start=2):
                alt_explanation = self._explain_ranked_model(
                    candidate, rank=i, is_primary=False
                )
                report.alternatives.append(alt_explanation)

        # Explain rejections (top 5 most relevant)
        relevant_rejected = self._filter_relevant_rejections(rejected, use_case)
        for rej in relevant_rejected[:5]:
            rej_explanation = self._explain_rejection(rej)
            report.rejected_models.append(rej_explanation)

        # Improvement suggestions
        report.improvement_suggestions = self._generate_improvement_suggestions(
            ranked, rejected, hardware
        )

        return report

    def _summarize_hardware(self, hardware: HardwareProfile) -> str:
        """Generate hardware summary string."""
        parts = []

        # GPU
        if hardware.gpu_name != "Unknown":
            parts.append(f"{hardware.gpu_name} ({hardware.vram_gb:.0f}GB VRAM)")
        else:
            parts.append("No dedicated GPU detected")

        # Platform
        platform_names = {
            PlatformType.NVIDIA: "NVIDIA CUDA",
            PlatformType.APPLE_SILICON: "Apple Silicon",
            PlatformType.AMD_ROCM: "AMD ROCm",
            PlatformType.CPU_ONLY: "CPU Only",
        }
        parts.append(platform_names.get(hardware.platform, str(hardware.platform)))

        # RAM
        if hardware.ram:
            parts.append(f"{hardware.ram.total_gb:.0f}GB RAM")
            if hardware.ram.usable_for_offload_gb > 0:
                parts.append(
                    f"({hardware.ram.usable_for_offload_gb:.0f}GB available for offload)"
                )

        # Storage
        if hardware.storage:
            tier_names = {
                StorageTier.FAST: "Fast (NVMe)",
                StorageTier.MODERATE: "Moderate (SATA SSD)",
                StorageTier.SLOW: "Slow (HDD)",
            }
            parts.append(
                f"{hardware.storage.free_gb:.0f}GB free space "
                f"({tier_names.get(hardware.storage.tier, 'Unknown')})"
            )

        return " | ".join(parts)

    def _explain_ranked_model(
        self,
        ranked: RankedCandidate,
        rank: int,
        is_primary: bool,
    ) -> ModelExplanation:
        """Generate explanation for a ranked model."""
        model = ranked.scored_candidate.passing_candidate.model
        variant = ranked.scored_candidate.passing_candidate.variant

        explanation = ModelExplanation(
            model_id=model.id,
            model_name=model.name,
            rank=rank,
            score=ranked.closeness_coefficient,
            is_recommended=True,
        )

        # Summary
        if is_primary:
            explanation.summary = (
                f"{model.name} is your best match with a {ranked.closeness_coefficient:.0%} "
                f"compatibility score."
            )
        else:
            explanation.summary = (
                f"{model.name} is an alternative option "
                f"({ranked.closeness_coefficient:.0%} compatibility)."
            )

        # Explain top contributing factors
        top_criteria = sorted(
            ranked.criterion_scores.values(),
            key=lambda c: c.weighted_score,
            reverse=True
        )[:3]

        for cs in top_criteria:
            criterion_name = self.CRITERION_NAMES.get(
                cs.criterion_id, cs.criterion_id.replace("_", " ").title()
            )
            strength = self._score_to_strength(cs.raw_score)

            explanation.items.append(ExplanationItem(
                type=ExplanationType.RECOMMENDATION,
                title=criterion_name,
                description=f"{strength} ({cs.raw_score:.0%})",
                priority=int(cs.weighted_score * 100),
            ))

        # Feature matches from content layer
        matches = ranked.scored_candidate.matching_features[:3]
        for match in matches:
            feature_name = match.feature_id.replace("_", " ").title()
            explanation.items.append(ExplanationItem(
                type=ExplanationType.RECOMMENDATION,
                title=f"Strong {feature_name}",
                description=f"Model scores {match.model_value:.0%} vs your preference of {match.user_value:.0%}",
                priority=int(match.contribution * 100),
            ))

        # Warnings
        passing = ranked.scored_candidate.passing_candidate
        if passing.warnings:
            for warning in passing.warnings:
                explanation.items.append(ExplanationItem(
                    type=ExplanationType.WARNING,
                    title="Note",
                    description=warning,
                    priority=50,
                ))

        # Execution mode info
        if passing.execution_mode == "gpu_offload":
            explanation.items.append(ExplanationItem(
                type=ExplanationType.WARNING,
                title="CPU Offload Active",
                description=(
                    "This model will use CPU RAM for some layers. "
                    "Generation will be 5-10x slower than native GPU."
                ),
                priority=80,
            ))

        # Variant info
        explanation.items.append(ExplanationItem(
            type=ExplanationType.TRADE_OFF,
            title="Selected Variant",
            description=f"{variant.precision} ({variant.vram_min_mb}MB minimum VRAM)",
            priority=30,
        ))

        # Sort items by priority
        explanation.items.sort(key=lambda x: x.priority, reverse=True)

        return explanation

    def _explain_rejection(self, rejected: RejectedCandidate) -> ModelExplanation:
        """Generate explanation for a rejected model."""
        model = rejected.model

        explanation = ModelExplanation(
            model_id=model.id,
            model_name=model.name,
            rank=0,
            score=0.0,
            is_recommended=False,
        )

        # Main rejection reason
        reason_message = self.REJECTION_MESSAGES.get(
            rejected.reason,
            rejected.reason.value.replace("_", " ").title()
        )

        explanation.summary = f"{model.name} was excluded: {reason_message}"

        explanation.items.append(ExplanationItem(
            type=ExplanationType.REJECTION,
            title="Excluded",
            description=reason_message,
            details=rejected.details,
            priority=100,
        ))

        # Add details
        if rejected.details:
            explanation.items.append(ExplanationItem(
                type=ExplanationType.REJECTION,
                title="Details",
                description=rejected.details,
                priority=90,
            ))

        return explanation

    def _filter_relevant_rejections(
        self,
        rejected: List[RejectedCandidate],
        use_case: str,
    ) -> List[RejectedCandidate]:
        """Filter rejections to most relevant for use case."""
        # For now, return all. Could be filtered by model family/use case match.
        return rejected

    def _generate_improvement_suggestions(
        self,
        ranked: List[RankedCandidate],
        rejected: List[RejectedCandidate],
        hardware: HardwareProfile,
    ) -> List[ExplanationItem]:
        """Generate suggestions for improving recommendations."""
        suggestions = []

        # Check if VRAM is limiting
        vram_rejections = [
            r for r in rejected
            if r.reason == RejectionReason.INSUFFICIENT_VRAM
        ]

        if vram_rejections:
            # Find how much VRAM would help
            needed_vram = []
            for r in vram_rejections:
                for v in r.model.variants:
                    needed_vram.append(v.vram_min_mb)

            if needed_vram:
                min_needed = min(needed_vram) / 1024  # Convert to GB
                current = hardware.vram_gb

                if min_needed <= 24:
                    suggestions.append(ExplanationItem(
                        type=ExplanationType.IMPROVEMENT,
                        title="GPU Upgrade Would Help",
                        description=(
                            f"With {min_needed:.0f}GB+ VRAM, you could run "
                            f"{len(vram_rejections)} additional models."
                        ),
                        details=(
                            f"Current: {current:.0f}GB VRAM. "
                            f"Consider RTX 4070 Ti Super (16GB) or RTX 4090 (24GB)."
                        ),
                        priority=90,
                    ))

        # Check storage limitations
        storage_rejections = [
            r for r in rejected
            if r.reason == RejectionReason.INSUFFICIENT_STORAGE
        ]

        if storage_rejections and hardware.storage:
            suggestions.append(ExplanationItem(
                type=ExplanationType.IMPROVEMENT,
                title="More Disk Space Needed",
                description=(
                    f"{len(storage_rejections)} models need more storage. "
                    f"Current free: {hardware.storage.free_gb:.0f}GB."
                ),
                details="Consider adding an NVMe SSD for model storage.",
                priority=70,
            ))

        # Check if offload is being used
        offload_models = [
            r for r in ranked
            if r.scored_candidate.passing_candidate.execution_mode == "gpu_offload"
        ]

        if offload_models:
            suggestions.append(ExplanationItem(
                type=ExplanationType.IMPROVEMENT,
                title="Models Running with CPU Offload",
                description=(
                    f"{len(offload_models)} models are using CPU offload, "
                    "which is 5-10x slower than native GPU."
                ),
                details="A GPU with more VRAM would eliminate offload slowdown.",
                priority=80,
            ))

        # Apple Silicon specific
        if hardware.platform == PlatformType.APPLE_SILICON:
            mps_rejections = [
                r for r in rejected
                if r.reason == RejectionReason.MPS_KQUANT_CRASH
            ]

            if mps_rejections:
                suggestions.append(ExplanationItem(
                    type=ExplanationType.IMPROVEMENT,
                    title="K-Quant Models Unavailable",
                    description=(
                        f"{len(mps_rejections)} models use K-quant formats "
                        "that crash on Apple Silicon."
                    ),
                    details=(
                        "These models work on NVIDIA GPUs. "
                        "Q4_0, Q5_0, and Q8_0 formats are safe on Mac."
                    ),
                    priority=60,
                ))

        return suggestions

    def _score_to_strength(self, score: float) -> str:
        """Convert 0-1 score to human-readable strength."""
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.6:
            return "Good"
        elif score >= 0.4:
            return "Moderate"
        elif score >= 0.2:
            return "Limited"
        else:
            return "Poor"

    def format_as_text(self, report: RecommendationReport) -> str:
        """Format report as plain text for display."""
        lines = []

        # Hardware summary
        lines.append("=" * 60)
        lines.append("HARDWARE PROFILE")
        lines.append("=" * 60)
        lines.append(report.hardware_summary)
        lines.append("")

        # Primary recommendation
        if report.primary_recommendation:
            lines.append("=" * 60)
            lines.append("TOP RECOMMENDATION")
            lines.append("=" * 60)
            lines.extend(self._format_model_explanation(report.primary_recommendation))
            lines.append("")

        # Alternatives
        if report.alternatives:
            lines.append("=" * 60)
            lines.append("ALTERNATIVES")
            lines.append("=" * 60)
            for alt in report.alternatives:
                lines.extend(self._format_model_explanation(alt, compact=True))
                lines.append("")

        # Improvement suggestions
        if report.improvement_suggestions:
            lines.append("=" * 60)
            lines.append("SUGGESTIONS FOR IMPROVEMENT")
            lines.append("=" * 60)
            for suggestion in report.improvement_suggestions:
                lines.append(f"• {suggestion.title}")
                lines.append(f"  {suggestion.description}")
                if suggestion.details:
                    lines.append(f"  → {suggestion.details}")
                lines.append("")

        return "\n".join(lines)

    def _format_model_explanation(
        self,
        explanation: ModelExplanation,
        compact: bool = False,
    ) -> List[str]:
        """Format single model explanation as text lines."""
        lines = []

        lines.append(f"#{explanation.rank}: {explanation.model_name}")
        lines.append(f"   Score: {explanation.score:.0%}")
        lines.append(f"   {explanation.summary}")

        if not compact:
            for item in explanation.items[:5]:
                prefix = "✓" if item.type == ExplanationType.RECOMMENDATION else "!"
                if item.type == ExplanationType.WARNING:
                    prefix = "⚠"
                elif item.type == ExplanationType.REJECTION:
                    prefix = "✗"
                lines.append(f"   {prefix} {item.title}: {item.description}")

        return lines
