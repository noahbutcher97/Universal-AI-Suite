"""
Resolution Cascade for handling constraint failures.

When a model fails Layer 1 constraints, this cascade attempts to find
alternatives in order of preference:

1. Quantization - Use a lower-precision variant of the same model
2. CPU Offload - Offload layers to CPU RAM (5-10x slower)
3. Substitution - Recommend a similar but lighter model
4. Workflow Adjustment - Suggest workflow changes (lower resolution, etc.)
5. Cloud Fallback - Recommend cloud API alternative

Per SPEC_v3 Section 6.5.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Set

from src.schemas.hardware import HardwareProfile, PlatformType
from src.services.model_database import ModelEntry, ModelVariant


class ResolutionStrategy(Enum):
    """Available resolution strategies in cascade order."""
    QUANTIZATION = "quantization"
    CPU_OFFLOAD = "cpu_offload"
    SUBSTITUTION = "substitution"
    WORKFLOW_ADJUSTMENT = "workflow_adjustment"
    CLOUD_FALLBACK = "cloud_fallback"


@dataclass
class ResolutionAttempt:
    """Record of a resolution attempt."""
    strategy: ResolutionStrategy
    success: bool
    result: Optional[str] = None  # Model ID or description
    details: str = ""
    performance_impact: str = ""  # e.g., "5-10x slower", "Lower quality"


@dataclass
class ResolutionResult:
    """Result of the resolution cascade."""
    original_model_id: str
    resolved: bool
    final_strategy: Optional[ResolutionStrategy] = None
    resolved_model_id: Optional[str] = None
    resolved_variant: Optional[ModelVariant] = None
    attempts: List[ResolutionAttempt] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    user_message: str = ""


# Substitution mappings: model_family -> lighter alternatives
# Format: {family: [(lighter_family, quality_ratio), ...]}
SUBSTITUTION_MAP: Dict[str, List[Tuple[str, float]]] = {
    # High-end image models -> mid-tier alternatives
    "flux": [
        ("flux_schnell", 0.85),  # Same family, faster variant
        ("sdxl", 0.75),          # Different architecture, lighter
    ],
    "flux_dev": [
        ("flux_schnell", 0.90),
        ("sdxl", 0.75),
    ],
    "sdxl": [
        ("sd15", 0.65),
    ],
    # Video models -> lighter alternatives
    "hunyuan_video": [
        ("wan21", 0.80),
        ("animatediff", 0.60),
    ],
    "wan21": [
        ("animatediff", 0.75),
    ],
    "cogvideox": [
        ("wan21", 0.85),
        ("animatediff", 0.65),
    ],
    # No substitution available
    "sd15": [],
    "animatediff": [],
}

# Cloud fallback options by capability
CLOUD_FALLBACKS: Dict[str, Dict[str, str]] = {
    "image_generation": {
        "partner_node": "ComfyUI Cloud (Partner Nodes)",
        "replicate": "Replicate API",
        "stability": "Stability AI API",
    },
    "video_generation": {
        "partner_node": "ComfyUI Cloud (Partner Nodes)",
        "replicate": "Replicate API",
        "runway": "Runway API",
    },
}

# Workflow adjustment suggestions
WORKFLOW_ADJUSTMENTS: Dict[str, Dict[str, str]] = {
    "reduce_resolution": {
        "description": "Generate at lower resolution, then upscale",
        "from": "1024x1024",
        "to": "768x768 or 512x512",
        "impact": "Faster generation, may lose fine details",
    },
    "reduce_batch": {
        "description": "Generate fewer images per batch",
        "from": "4+ images",
        "to": "1-2 images",
        "impact": "Lower VRAM usage, slower throughput",
    },
    "reduce_steps": {
        "description": "Use fewer inference steps",
        "from": "30+ steps",
        "to": "15-20 steps",
        "impact": "Faster generation, may affect quality",
    },
    "video_shorter": {
        "description": "Generate shorter video clips",
        "from": "4+ seconds",
        "to": "2 seconds",
        "impact": "Lower VRAM usage, more clips needed",
    },
}


class ResolutionCascade:
    """
    Attempts to resolve constraint failures through a cascade of strategies.

    The cascade order (SPEC_v3 Section 6.5):
    1. Quantization - Try lower precision variant
    2. CPU Offload - Use RAM for layer offloading
    3. Substitution - Find similar lighter model
    4. Workflow - Suggest workflow changes
    5. Cloud - Fall back to cloud API
    """

    # Quantization priority (higher precision first)
    QUANT_PRIORITY = ["fp16", "bf16", "fp8", "q8_0", "q5_0", "q4_0"]

    # Apple Silicon safe quants (K-quants crash MPS)
    MPS_SAFE_QUANTS: Set[str] = {"q4_0", "q5_0", "q8_0", "f16", "f32", "fp16", "bf16"}

    def __init__(self, model_database: Dict[str, ModelEntry]):
        """
        Initialize cascade with model database.

        Args:
            model_database: Dict mapping model_id to ModelEntry
        """
        self.model_db = model_database

    def resolve(
        self,
        model: ModelEntry,
        hardware: HardwareProfile,
        failure_reason: str,
        use_case: str,
    ) -> ResolutionResult:
        """
        Attempt to resolve a constraint failure.

        Args:
            model: The model that failed constraints
            hardware: User's hardware profile
            failure_reason: Why the model failed (from Layer 1)
            use_case: The use case being served

        Returns:
            ResolutionResult with resolution attempts and outcome
        """
        result = ResolutionResult(
            original_model_id=model.id,
            resolved=False,
            attempts=[],
            warnings=[],
        )

        vram_mb = int(hardware.vram_gb * 1024)
        is_apple_silicon = hardware.platform == PlatformType.APPLE_SILICON

        # Strategy 1: Try quantization
        quant_result = self._try_quantization(model, vram_mb, is_apple_silicon)
        result.attempts.append(quant_result)

        if quant_result.success:
            result.resolved = True
            result.final_strategy = ResolutionStrategy.QUANTIZATION
            result.resolved_model_id = model.id
            result.resolved_variant = self._find_variant_by_precision(
                model, quant_result.result
            )
            result.user_message = (
                f"Using {quant_result.result} quantized variant. "
                f"{quant_result.performance_impact}"
            )
            return result

        # Strategy 2: Try CPU offload
        if hardware.ram is not None:
            offload_result = self._try_cpu_offload(model, hardware)
            result.attempts.append(offload_result)

            if offload_result.success:
                result.resolved = True
                result.final_strategy = ResolutionStrategy.CPU_OFFLOAD
                result.resolved_model_id = model.id
                result.resolved_variant = self._find_variant_by_precision(
                    model, offload_result.result
                )
                result.warnings.append(
                    "CPU offload active - expect 5-10x slower generation"
                )
                result.user_message = (
                    f"Using CPU offload with {offload_result.result} variant. "
                    "Generation will be 5-10x slower than native GPU."
                )
                return result

        # Strategy 3: Try substitution
        sub_result = self._try_substitution(model, vram_mb, use_case, is_apple_silicon)
        result.attempts.append(sub_result)

        if sub_result.success:
            result.resolved = True
            result.final_strategy = ResolutionStrategy.SUBSTITUTION
            result.resolved_model_id = sub_result.result
            # Find the substituted model
            if sub_result.result in self.model_db:
                sub_model = self.model_db[sub_result.result]
                result.resolved_variant = self._find_best_fitting_variant(
                    sub_model, vram_mb, is_apple_silicon
                )
            result.warnings.append(
                f"Using {sub_result.result} as substitute for {model.id}"
            )
            result.user_message = sub_result.details
            return result

        # Strategy 4: Suggest workflow adjustment
        workflow_result = self._suggest_workflow_adjustment(model, hardware, use_case)
        result.attempts.append(workflow_result)

        if workflow_result.success:
            result.resolved = True
            result.final_strategy = ResolutionStrategy.WORKFLOW_ADJUSTMENT
            result.resolved_model_id = model.id
            result.user_message = workflow_result.details
            result.warnings.append("Workflow adjustments required - see details")
            return result

        # Strategy 5: Cloud fallback
        cloud_result = self._suggest_cloud_fallback(model, use_case)
        result.attempts.append(cloud_result)

        if cloud_result.success:
            result.resolved = True
            result.final_strategy = ResolutionStrategy.CLOUD_FALLBACK
            result.user_message = cloud_result.details
            result.warnings.append(
                "Local generation not possible - cloud API recommended"
            )
            return result

        # All strategies failed
        result.user_message = (
            f"Unable to run {model.name} on your hardware. "
            "No suitable alternatives found."
        )
        return result

    def _try_quantization(
        self,
        model: ModelEntry,
        vram_mb: int,
        is_apple_silicon: bool,
    ) -> ResolutionAttempt:
        """Try to find a quantized variant that fits."""
        attempt = ResolutionAttempt(
            strategy=ResolutionStrategy.QUANTIZATION,
            success=False,
        )

        # Get available quantizations for this model
        available_quants = []
        for variant in model.variants:
            precision = variant.precision.lower()
            # Skip K-quants on Apple Silicon
            if is_apple_silicon and precision not in self.MPS_SAFE_QUANTS:
                continue
            if variant.vram_min_mb <= vram_mb:
                available_quants.append((precision, variant.vram_min_mb))

        if not available_quants:
            attempt.details = "No quantized variants fit available VRAM"
            return attempt

        # Sort by quality (higher precision = higher quality)
        for quant in self.QUANT_PRIORITY:
            for precision, vram_req in available_quants:
                if precision == quant:
                    attempt.success = True
                    attempt.result = precision
                    attempt.details = f"Found {precision} variant ({vram_req}MB VRAM)"
                    attempt.performance_impact = self._get_quant_impact(precision)
                    return attempt

        # Fall back to lowest VRAM option
        available_quants.sort(key=lambda x: x[1])
        precision, vram_req = available_quants[0]
        attempt.success = True
        attempt.result = precision
        attempt.details = f"Using {precision} variant ({vram_req}MB VRAM)"
        attempt.performance_impact = self._get_quant_impact(precision)
        return attempt

    def _try_cpu_offload(
        self,
        model: ModelEntry,
        hardware: HardwareProfile,
    ) -> ResolutionAttempt:
        """Try to run with CPU offload."""
        attempt = ResolutionAttempt(
            strategy=ResolutionStrategy.CPU_OFFLOAD,
            success=False,
        )

        if hardware.ram is None:
            attempt.details = "RAM profile not available"
            return attempt

        vram_mb = int(hardware.vram_gb * 1024)
        offload_gb = hardware.ram.usable_for_offload_gb
        effective_mb = vram_mb + int(offload_gb * 1024)

        # Find variant that fits with offload
        best_variant = None
        for variant in model.variants:
            if variant.vram_min_mb <= effective_mb:
                if best_variant is None or variant.vram_min_mb > best_variant.vram_min_mb:
                    best_variant = variant

        if best_variant is None:
            attempt.details = (
                f"No variants fit even with offload "
                f"(effective: {effective_mb}MB)"
            )
            return attempt

        # Check if it actually needed offload (not native)
        if best_variant.vram_min_mb <= vram_mb:
            attempt.details = "Variant fits natively, offload not needed"
            return attempt

        attempt.success = True
        attempt.result = best_variant.precision
        attempt.details = (
            f"Can run {best_variant.precision} with CPU offload "
            f"({best_variant.vram_min_mb}MB total, {vram_mb}MB GPU + "
            f"{best_variant.vram_min_mb - vram_mb}MB offloaded)"
        )
        attempt.performance_impact = "5-10x slower than native GPU"
        return attempt

    def _try_substitution(
        self,
        model: ModelEntry,
        vram_mb: int,
        use_case: str,
        is_apple_silicon: bool,
    ) -> ResolutionAttempt:
        """Try to find a substitute model."""
        attempt = ResolutionAttempt(
            strategy=ResolutionStrategy.SUBSTITUTION,
            success=False,
        )

        family = model.family.lower()
        substitutes = SUBSTITUTION_MAP.get(family, [])

        if not substitutes:
            attempt.details = f"No substitutes defined for {family}"
            return attempt

        for sub_family, quality_ratio in substitutes:
            # Find models in substitute family
            for model_id, candidate in self.model_db.items():
                if candidate.family.lower() != sub_family:
                    continue

                # Check if substitute fits
                fitting_variant = self._find_best_fitting_variant(
                    candidate, vram_mb, is_apple_silicon
                )
                if fitting_variant:
                    attempt.success = True
                    attempt.result = model_id
                    attempt.details = (
                        f"Recommend {candidate.name} as substitute "
                        f"(~{int(quality_ratio * 100)}% quality vs {model.name})"
                    )
                    attempt.performance_impact = (
                        f"Different model, approximately {int(quality_ratio * 100)}% "
                        "comparable output quality"
                    )
                    return attempt

        attempt.details = "No fitting substitutes found in database"
        return attempt

    def _suggest_workflow_adjustment(
        self,
        model: ModelEntry,
        hardware: HardwareProfile,
        use_case: str,
    ) -> ResolutionAttempt:
        """Suggest workflow changes to make model fit."""
        attempt = ResolutionAttempt(
            strategy=ResolutionStrategy.WORKFLOW_ADJUSTMENT,
            success=False,
        )

        suggestions = []
        vram_mb = int(hardware.vram_gb * 1024)

        # Find smallest variant
        min_vram = min(v.vram_min_mb for v in model.variants) if model.variants else 0
        vram_gap = min_vram - vram_mb

        if vram_gap <= 0:
            attempt.details = "Model should fit, no adjustments needed"
            return attempt

        # Suggest based on VRAM gap
        if vram_gap <= 2048:  # Within 2GB
            if "image" in use_case.lower():
                suggestions.append(WORKFLOW_ADJUSTMENTS["reduce_resolution"])
                suggestions.append(WORKFLOW_ADJUSTMENTS["reduce_batch"])
            elif "video" in use_case.lower():
                suggestions.append(WORKFLOW_ADJUSTMENTS["video_shorter"])
                suggestions.append(WORKFLOW_ADJUSTMENTS["reduce_resolution"])

        if vram_gap <= 4096:  # Within 4GB
            suggestions.append(WORKFLOW_ADJUSTMENTS["reduce_steps"])

        if not suggestions:
            attempt.details = (
                f"VRAM gap too large ({vram_gap}MB) for workflow adjustments"
            )
            return attempt

        attempt.success = True
        attempt.result = "workflow_changes"
        attempt.details = "Suggested workflow adjustments:\n"
        for s in suggestions:
            attempt.details += f"- {s['description']}: {s['from']} -> {s['to']}\n"
        attempt.performance_impact = "; ".join(s["impact"] for s in suggestions)
        return attempt

    def _suggest_cloud_fallback(
        self,
        model: ModelEntry,
        use_case: str,
    ) -> ResolutionAttempt:
        """Suggest cloud API alternatives."""
        attempt = ResolutionAttempt(
            strategy=ResolutionStrategy.CLOUD_FALLBACK,
            success=False,
        )

        # Determine category
        category = "image_generation"
        if any(tag in use_case.lower() for tag in ["video", "animation"]):
            category = "video_generation"

        fallbacks = CLOUD_FALLBACKS.get(category, {})

        # Check model's cloud support first
        cloud_options = []
        if hasattr(model, 'cloud') and model.cloud:
            if model.cloud.partner_node:
                cloud_options.append(("partner_node", "ComfyUI Partner Nodes (native workflow)"))
            if model.cloud.replicate:
                cloud_options.append(("replicate", model.cloud.replicate))

        # Add generic fallbacks
        for key, name in fallbacks.items():
            if key not in [c[0] for c in cloud_options]:
                cloud_options.append((key, name))

        if not cloud_options:
            attempt.details = "No cloud fallbacks available for this use case"
            return attempt

        attempt.success = True
        attempt.result = cloud_options[0][0]
        attempt.details = "Cloud alternatives available:\n"
        for key, name in cloud_options[:3]:  # Top 3
            attempt.details += f"- {name}\n"
        attempt.performance_impact = "Requires internet, may incur costs"
        return attempt

    def _find_variant_by_precision(
        self,
        model: ModelEntry,
        precision: str,
    ) -> Optional[ModelVariant]:
        """Find variant matching precision string."""
        precision_lower = precision.lower()
        for variant in model.variants:
            if variant.precision.lower() == precision_lower:
                return variant
        return None

    def _find_best_fitting_variant(
        self,
        model: ModelEntry,
        vram_mb: int,
        is_apple_silicon: bool,
    ) -> Optional[ModelVariant]:
        """Find best variant that fits VRAM."""
        fitting = []
        for variant in model.variants:
            precision = variant.precision.lower()
            # Skip K-quants on Apple Silicon
            if is_apple_silicon and precision not in self.MPS_SAFE_QUANTS:
                continue
            if variant.vram_min_mb <= vram_mb:
                fitting.append(variant)

        if not fitting:
            return None

        # Return highest VRAM (best quality) that fits
        fitting.sort(key=lambda v: v.vram_min_mb, reverse=True)
        return fitting[0]

    def _get_quant_impact(self, precision: str) -> str:
        """Get performance impact description for quantization level."""
        impacts = {
            "fp16": "Minimal quality loss",
            "bf16": "Minimal quality loss",
            "fp8": "Slight quality reduction, ~30% faster",
            "q8_0": "Minor quality loss, ~40% less VRAM",
            "q5_0": "Noticeable quality loss, ~50% less VRAM",
            "q4_0": "Significant quality loss, ~60% less VRAM",
        }
        return impacts.get(precision.lower(), "Quality impact varies")


def create_cascade_for_hardware(
    hardware: HardwareProfile,
    model_database: Dict[str, ModelEntry],
) -> ResolutionCascade:
    """Factory function to create cascade instance."""
    return ResolutionCascade(model_database)
