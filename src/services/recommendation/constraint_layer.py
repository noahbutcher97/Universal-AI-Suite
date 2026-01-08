"""
Layer 1: Constraint Satisfaction Layer (CSP).

Binary elimination based on hard constraints per SPEC_v3 Section 6.2.
Filters out models that cannot run on the user's hardware.

Constraints checked:
- VRAM requirements (with quantization fallback paths)
- Platform compatibility (Apple Silicon exclusions)
- Compute capability (FP8 on CC 8.9+)
- CPU offload viability
- Storage space
- K-quant filtering for Apple Silicon (MPS crashes on K-quants)
- Model exclusions for Apple Silicon (e.g., HunyuanVideo)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum

from src.schemas.hardware import HardwareProfile, CPUTier, PlatformType
from src.services.model_database import ModelEntry, ModelVariant, ModelDatabase


# =============================================================================
# Apple Silicon Constraints (SPEC_v3 Section 4.2, HARDWARE_DETECTION.md)
# =============================================================================

# Safe GGUF quantizations for Apple Silicon MPS
# K-quants (Q4_K_M, Q5_K_S, Q6_K, etc.) crash MPS - only non-K variants are safe
# Per SPEC_v3 Section 4.2: "Filter to Q4_0, Q5_0, Q8_0 only (K-quants crash MPS)"
MPS_SAFE_GGUF_QUANTS: Set[str] = {
    "q4_0",
    "q5_0",
    "q8_0",
    "f16",  # Full precision is always safe
    "f32",
}

# K-quant patterns that crash on MPS
# These use the "K" quantization method which is incompatible with Metal
MPS_UNSAFE_GGUF_PATTERNS: Set[str] = {
    "_k_",   # Q4_K_M, Q5_K_S, Q6_K, etc.
    "_k.",   # Q4_K.gguf at end of filename
    "iq",    # IQ quantization variants (IQ2_XXS, IQ3_M, etc.)
}

# Models excluded from Apple Silicon due to impractical performance
# Per SPEC_v3 Section 4.2: "Exclude HunyuanVideo (~16 min/clip) - use AnimateDiff instead"
APPLE_SILICON_EXCLUDED_MODELS: Dict[str, str] = {
    "hunyuan_video": "~16 min/clip generation time - consider AnimateDiff or Wan2.1 instead",
    "hunyuanvideo": "~16 min/clip generation time - consider AnimateDiff or Wan2.1 instead",
}

# Alternative suggestions for excluded models
APPLE_SILICON_ALTERNATIVES: Dict[str, List[str]] = {
    "hunyuan_video": ["animatediff", "wan_21_t2v"],
    "hunyuanvideo": ["animatediff", "wan_21_t2v"],
}


class RejectionReason(Enum):
    """Reasons a model candidate was rejected."""
    VRAM_INSUFFICIENT = "vram_insufficient"
    PLATFORM_UNSUPPORTED = "platform_unsupported"
    COMPUTE_CAPABILITY = "compute_capability"
    STORAGE_INSUFFICIENT = "storage_insufficient"
    CPU_CANNOT_OFFLOAD = "cpu_cannot_offload"
    QUANTIZATION_UNAVAILABLE = "quantization_unavailable"
    PAIRED_MODEL_MISSING = "paired_model_missing"
    MPS_KQUANT_CRASH = "mps_kquant_crash"  # K-quant on Apple Silicon
    APPLE_SILICON_EXCLUDED = "apple_silicon_excluded"  # Model excluded for Apple Silicon


@dataclass
class RejectedCandidate:
    """A model that was rejected with explanation."""
    model_id: str
    model_name: str
    reason: RejectionReason
    details: str
    suggestion: Optional[str] = None  # e.g., "Consider GGUF Q4 variant"


@dataclass
class PassingCandidate:
    """A model that passed constraint satisfaction."""
    model: ModelEntry
    variant: ModelVariant
    execution_mode: str = "native"  # "native", "quantized", "gpu_offload"
    warnings: List[str] = field(default_factory=list)


class ConstraintSatisfactionLayer:
    """
    Layer 1: Constraint Satisfaction.

    Performs binary elimination on model candidates based on hardware constraints.
    Returns only models that CAN run on the hardware, along with rejected candidates
    and reasons for rejection.

    SPEC_v3 Section 6.2:
    - VRAM constraint: model.vram_min_mb <= hardware.vram_mb
    - Platform constraint: variant.platform_support[platform].supported == True
    - Compute capability: variant.min_compute_capability <= hardware.compute_capability
    - Storage constraint: model.download_size_gb <= hardware.free_storage_gb
    """

    def __init__(self, model_db: ModelDatabase):
        """
        Initialize the constraint layer.

        Args:
            model_db: The model database to query
        """
        self.model_db = model_db

    def filter(
        self,
        hardware: HardwareProfile,
        categories: Optional[List[str]] = None,
        commercial_only: bool = False,
    ) -> Tuple[List[PassingCandidate], List[RejectedCandidate]]:
        """
        Filter models by hardware constraints.

        Args:
            hardware: The user's hardware profile
            categories: Model categories to consider (None = all)
            commercial_only: Only include commercially-licensed models

        Returns:
            Tuple of (passing_candidates, rejected_candidates)
        """
        # TODO: Implement in Phase 3
        # This is a stub implementation
        passing: List[PassingCandidate] = []
        rejected: List[RejectedCandidate] = []

        # Get platform key
        platform = self._get_platform_key(hardware)

        # Get VRAM in MB
        vram_mb = int(hardware.vram_gb * 1024)

        # Get compute capability
        compute_cap = hardware.compute_capability

        # Iterate through all models
        for model in self.model_db.iter_models():
            # Skip cloud-only models
            if not model.variants:
                continue

            # Category filter
            if categories and model.category not in categories:
                continue

            # Commercial filter
            if commercial_only and not model.commercial_use:
                continue

            # Try to find a viable variant
            result = self._check_model(model, platform, vram_mb, compute_cap, hardware)

            if isinstance(result, PassingCandidate):
                passing.append(result)
            else:
                rejected.append(result)

        return passing, rejected

    def _check_model(
        self,
        model: ModelEntry,
        platform: str,
        vram_mb: int,
        compute_cap: Optional[float],
        hardware: HardwareProfile,
    ) -> PassingCandidate | RejectedCandidate:
        """
        Check if a model can run on the hardware.

        Constraint checks in order:
        1. Apple Silicon exclusions (e.g., HunyuanVideo)
        2. Platform compatibility
        3. K-quant filtering for Apple Silicon MPS
        4. VRAM requirements
        5. Compute capability

        Tries variants in order of quality retention (highest first).
        If native variant fails, tries quantized variants.
        If all variants fail, returns a RejectedCandidate.
        """
        is_apple = self._is_apple_silicon(hardware)

        # =================================================================
        # Check 1: Apple Silicon model exclusions
        # Per SPEC_v3 Section 4.2: Exclude HunyuanVideo (~16 min/clip)
        # =================================================================
        if is_apple:
            is_excluded, exclusion_reason = self._is_apple_silicon_excluded(model)
            if is_excluded:
                alternatives = self._get_apple_silicon_alternatives(model)
                suggestion = None
                if alternatives:
                    suggestion = f"Consider: {', '.join(alternatives)}"

                return RejectedCandidate(
                    model_id=model.id,
                    model_name=model.name,
                    reason=RejectionReason.APPLE_SILICON_EXCLUDED,
                    details=exclusion_reason or "Excluded for Apple Silicon",
                    suggestion=suggestion,
                )

        # =================================================================
        # Check 2: Get compatible variants from database
        # =================================================================
        variants = self.model_db.get_compatible_variants(
            model, platform, vram_mb, compute_cap
        )

        # =================================================================
        # Check 3: Filter K-quants for Apple Silicon MPS
        # Per SPEC_v3 Section 4.2: K-quants crash MPS
        # =================================================================
        if is_apple and variants:
            original_count = len(variants)
            variants = self._filter_mps_safe_variants(variants)

            # If all variants were K-quants, generate specific rejection
            if not variants and original_count > 0:
                return RejectedCandidate(
                    model_id=model.id,
                    model_name=model.name,
                    reason=RejectionReason.MPS_KQUANT_CRASH,
                    details=(
                        "All available GGUF variants use K-quantization which "
                        "crashes on Apple Silicon MPS"
                    ),
                    suggestion=(
                        "Wait for non-K GGUF variant (Q4_0, Q5_0, Q8_0) or "
                        "use native PyTorch variant"
                    ),
                )

        # =================================================================
        # Check 4: Return best viable variant if any
        # =================================================================
        if variants:
            # Return best compatible variant
            best = variants[0]
            execution_mode = "native"

            # Check if this is a quantized variant
            if "gguf" in best.precision.lower() or "fp8" in best.precision.lower():
                execution_mode = "quantized"

            warnings = []

            # Add warnings for edge cases
            if best.quality_retention_percent < 90:
                warnings.append(
                    f"Using quantized variant ({best.precision}) - "
                    f"{best.quality_retention_percent}% quality retention"
                )

            # Add Apple Silicon specific warnings
            if is_apple:
                # Warn about GGUF performance on Apple Silicon
                if "gguf" in best.precision.lower():
                    warnings.append(
                        "GGUF models run via llama.cpp on Apple Silicon - "
                        "performance may vary"
                    )

            return PassingCandidate(
                model=model,
                variant=best,
                execution_mode=execution_mode,
                warnings=warnings,
            )

        # =================================================================
        # Check 5: Try CPU offload if no native variants fit
        # Per SPEC_v3 Section 6.5: Resolution cascade includes cpu_offload
        # =================================================================
        if self._can_offload_to_cpu(hardware, model):
            offload_variant = self._find_offload_variant(model, platform, hardware)
            if offload_variant:
                warnings = [
                    f"Model requires CPU offload (5-10x slower than native GPU)",
                    f"Using {offload_variant.precision} variant with partial GPU acceleration"
                ]

                # Add RAM usage warning
                if hardware.ram:
                    warnings.append(
                        f"Will use ~{hardware.ram.usable_for_offload_gb:.1f}GB RAM for offloading"
                    )

                return PassingCandidate(
                    model=model,
                    variant=offload_variant,
                    execution_mode="gpu_offload",
                    warnings=warnings,
                )

        # No compatible variant found
        return self._generate_rejection(model, platform, vram_mb, compute_cap, hardware)

    def _find_offload_variant(
        self,
        model: ModelEntry,
        platform: str,
        hardware: HardwareProfile,
    ) -> Optional[ModelVariant]:
        """
        Find a variant that can run with CPU offload.

        Looks for variants where:
        - VRAM requirement exceeds native VRAM but fits in effective capacity
        - Platform is supported
        - Variant supports offloading (typically GGUF or large PyTorch models)
        """
        if hardware.ram is None:
            return None

        vram_mb = int(hardware.vram_gb * 1024)
        offload_gb = hardware.ram.usable_for_offload_gb
        effective_mb = vram_mb + int(offload_gb * 1024)

        # Find variants that fit with offload but not natively
        offload_candidates = []
        for variant in model.variants:
            # Skip if platform not supported
            ps = variant.platform_support.get(platform)
            if not ps or not ps.supported:
                continue

            # Skip if fits in native VRAM (handled by native path)
            if variant.vram_min_mb <= vram_mb:
                continue

            # Check if fits with offload
            if variant.vram_min_mb <= effective_mb:
                offload_candidates.append(variant)

        if not offload_candidates:
            return None

        # Sort by quality retention (prefer higher quality)
        offload_candidates.sort(
            key=lambda v: v.quality_retention_percent,
            reverse=True
        )

        return offload_candidates[0]

    def _generate_rejection(
        self,
        model: ModelEntry,
        platform: str,
        vram_mb: int,
        compute_cap: Optional[float],
        hardware: Optional[HardwareProfile] = None,
    ) -> RejectedCandidate:
        """Generate a rejection with helpful details."""
        # Find the minimum VRAM variant to give useful feedback
        min_vram = float('inf')
        for variant in model.variants:
            if variant.vram_min_mb < min_vram:
                min_vram = variant.vram_min_mb

        if min_vram > vram_mb:
            # Build suggestion based on what might help
            suggestion = None
            if model.explanation and model.explanation.rejected_vram:
                suggestion = model.explanation.rejected_vram
            elif hardware and hardware.ram:
                # Check if more RAM would enable offload
                effective_mb = vram_mb + int(hardware.ram.usable_for_offload_gb * 1024)
                if min_vram <= effective_mb:
                    suggestion = (
                        f"CPU offload not viable (requires {min_vram}MB, "
                        f"effective capacity {effective_mb}MB). "
                        "Consider a more quantized variant or cloud execution."
                    )
                else:
                    suggestion = (
                        f"Consider a quantized variant or cloud execution. "
                        f"Your system has {vram_mb}MB VRAM + "
                        f"{hardware.ram.usable_for_offload_gb:.1f}GB offload capacity."
                    )

            return RejectedCandidate(
                model_id=model.id,
                model_name=model.name,
                reason=RejectionReason.VRAM_INSUFFICIENT,
                details=f"Requires {min_vram}MB VRAM, you have {vram_mb}MB",
                suggestion=suggestion,
            )

        # Platform issue
        return RejectedCandidate(
            model_id=model.id,
            model_name=model.name,
            reason=RejectionReason.PLATFORM_UNSUPPORTED,
            details=f"Not supported on {platform}",
            suggestion=model.explanation.rejected_platform if model.explanation else None,
        )

    def _get_platform_key(self, hardware: HardwareProfile) -> str:
        """Get the platform key for model compatibility checks."""
        from src.services.model_database import normalize_platform
        return normalize_platform(hardware.gpu_vendor, hardware.platform)

    def _is_apple_silicon(self, hardware: HardwareProfile) -> bool:
        """Check if hardware is Apple Silicon."""
        return hardware.platform == PlatformType.APPLE_SILICON

    def _is_apple_silicon_excluded(self, model: ModelEntry) -> Tuple[bool, Optional[str]]:
        """
        Check if model is excluded for Apple Silicon.

        Per SPEC_v3 Section 4.2: Exclude models with impractical performance.
        Example: HunyuanVideo (~16 min/clip)

        Returns:
            (is_excluded, reason) - reason is None if not excluded
        """
        model_id_lower = model.id.lower()
        model_name_lower = model.name.lower()

        for excluded_id, reason in APPLE_SILICON_EXCLUDED_MODELS.items():
            if excluded_id in model_id_lower or excluded_id in model_name_lower:
                return True, reason

        return False, None

    def _get_apple_silicon_alternatives(self, model: ModelEntry) -> List[str]:
        """Get alternative model suggestions for an excluded Apple Silicon model."""
        model_id_lower = model.id.lower()

        for excluded_id, alternatives in APPLE_SILICON_ALTERNATIVES.items():
            if excluded_id in model_id_lower:
                return alternatives

        return []

    def _is_safe_gguf_for_mps(self, variant: ModelVariant) -> bool:
        """
        Check if a GGUF variant is safe to run on Apple Silicon MPS.

        Per SPEC_v3 Section 4.2: K-quants crash MPS.
        Only Q4_0, Q5_0, Q8_0 (and F16/F32) are safe.

        Args:
            variant: The model variant to check

        Returns:
            True if safe to run on MPS, False if it would crash
        """
        precision_lower = variant.precision.lower()

        # Not a GGUF variant - assume safe
        if "gguf" not in precision_lower:
            return True

        # Check for known unsafe patterns
        for pattern in MPS_UNSAFE_GGUF_PATTERNS:
            if pattern in precision_lower:
                return False

        # Check if it's a known safe quant
        for safe_quant in MPS_SAFE_GGUF_QUANTS:
            if safe_quant in precision_lower:
                return True

        # If GGUF but not matching known safe patterns, be cautious
        # This handles edge cases like "gguf_q4_k_m" which should be unsafe
        return False

    def _filter_mps_safe_variants(
        self,
        variants: List[ModelVariant],
    ) -> List[ModelVariant]:
        """
        Filter variants to only include those safe for Apple Silicon MPS.

        Args:
            variants: List of model variants to filter

        Returns:
            Filtered list containing only MPS-safe variants
        """
        return [v for v in variants if self._is_safe_gguf_for_mps(v)]

    def _check_vram_constraint(
        self,
        variant: ModelVariant,
        vram_mb: int,
    ) -> bool:
        """Check if variant fits in VRAM."""
        return variant.vram_min_mb <= vram_mb

    def _check_platform_constraint(
        self,
        variant: ModelVariant,
        platform: str,
    ) -> bool:
        """Check platform support."""
        ps = variant.platform_support.get(platform)
        return ps is not None and ps.supported

    def _check_compute_capability(
        self,
        variant: ModelVariant,
        platform: str,
        compute_cap: Optional[float],
    ) -> bool:
        """Check compute capability requirement."""
        ps = variant.platform_support.get(platform)
        if not ps or not ps.min_compute_capability:
            return True
        if compute_cap is None:
            return False
        return compute_cap >= ps.min_compute_capability

    def _check_storage_constraint(
        self,
        variant: ModelVariant,
        free_storage_gb: float,
    ) -> bool:
        """Check storage space."""
        return variant.download_size_gb <= free_storage_gb

    def _can_offload_to_cpu(
        self,
        hardware: HardwareProfile,
        model: ModelEntry,
    ) -> bool:
        """
        Check if CPU offload is viable for this model.

        Requirements per SPEC:
        - CPU tier >= MEDIUM (8+ cores)
        - AVX2 support (for GGUF/llama.cpp)
        - Sufficient RAM for offload
        """
        if hardware.cpu is None:
            return False

        # Check CPU tier
        if hardware.cpu.tier.value < CPUTier.MEDIUM.value:
            return False

        # Check AVX2 for x86
        if hardware.cpu.architecture == "x86_64" and not hardware.cpu.supports_avx2:
            return False

        # Check RAM availability
        if hardware.ram is None:
            return False

        usable_ram = hardware.ram.usable_for_offload_gb
        if usable_ram < 4.0:  # Minimum 4GB for meaningful offload
            return False

        return True
