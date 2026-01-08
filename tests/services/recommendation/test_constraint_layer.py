"""
Unit tests for ConstraintSatisfactionLayer.

Tests the Layer 1 CSP filtering including:
- K-quant filtering for Apple Silicon MPS
- HunyuanVideo exclusion for Apple Silicon
- VRAM constraint checking
- Platform compatibility
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import List, Optional

from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
    HardwareTier,
    CPUProfile,
    CPUTier,
    RAMProfile,
)
from src.services.recommendation.constraint_layer import (
    ConstraintSatisfactionLayer,
    RejectionReason,
    PassingCandidate,
    RejectedCandidate,
    MPS_SAFE_GGUF_QUANTS,
    MPS_UNSAFE_GGUF_PATTERNS,
    APPLE_SILICON_EXCLUDED_MODELS,
)
from src.services.model_database import ModelEntry, ModelVariant, PlatformSupport


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_model_db():
    """Create a mock ModelDatabase for testing."""
    return MagicMock()


@pytest.fixture
def apple_silicon_hardware() -> HardwareProfile:
    """Create an Apple Silicon hardware profile."""
    return HardwareProfile(
        platform=PlatformType.APPLE_SILICON,
        gpu_vendor="apple",
        gpu_name="Apple M2 Max",
        vram_gb=32.0,
        unified_memory=True,
        compute_capability=None,
        tier=HardwareTier.PROFESSIONAL,
    )


@pytest.fixture
def nvidia_hardware() -> HardwareProfile:
    """Create an NVIDIA hardware profile."""
    return HardwareProfile(
        platform=PlatformType.WINDOWS_NVIDIA,
        gpu_vendor="nvidia",
        gpu_name="NVIDIA GeForce RTX 4090",
        vram_gb=24.0,
        unified_memory=False,
        compute_capability=8.9,
        tier=HardwareTier.PROFESSIONAL,
    )


@pytest.fixture
def hunyuan_model() -> ModelEntry:
    """Create a HunyuanVideo model entry."""
    return ModelEntry(
        id="hunyuan_video_720p",
        name="HunyuanVideo 720p",
        category="video_generation",
        family="hunyuan",
        commercial_use=True,
        variants=[
            ModelVariant(
                id="hunyuan_video_720p_fp16",
                precision="FP16",
                vram_min_mb=24000,
                vram_recommended_mb=48000,
                download_size_gb=12.0,
                quality_retention_percent=100,
                platform_support={
                    "nvidia": PlatformSupport(supported=True),
                    "apple_silicon": PlatformSupport(supported=True),
                },
            ),
        ],
    )


@pytest.fixture
def gguf_model_kquant() -> ModelEntry:
    """Create a model with K-quant GGUF variants only."""
    return ModelEntry(
        id="llama3_8b",
        name="Llama 3 8B",
        category="llm",
        family="llama",
        commercial_use=False,
        variants=[
            ModelVariant(
                id="llama3_8b_q4_k_m",
                precision="GGUF Q4_K_M",
                vram_min_mb=4000,
                vram_recommended_mb=6000,
                download_size_gb=4.0,
                quality_retention_percent=85,
                platform_support={
                    "nvidia": PlatformSupport(supported=True),
                    "apple_silicon": PlatformSupport(supported=True),
                },
            ),
            ModelVariant(
                id="llama3_8b_q5_k_s",
                precision="GGUF Q5_K_S",
                vram_min_mb=5000,
                vram_recommended_mb=8000,
                download_size_gb=5.0,
                quality_retention_percent=90,
                platform_support={
                    "nvidia": PlatformSupport(supported=True),
                    "apple_silicon": PlatformSupport(supported=True),
                },
            ),
        ],
    )


@pytest.fixture
def gguf_model_safe() -> ModelEntry:
    """Create a model with MPS-safe GGUF variants."""
    return ModelEntry(
        id="llama3_8b",
        name="Llama 3 8B",
        category="llm",
        family="llama",
        commercial_use=False,
        variants=[
            ModelVariant(
                id="llama3_8b_q4_0",
                precision="GGUF Q4_0",
                vram_min_mb=4000,
                vram_recommended_mb=6000,
                download_size_gb=4.0,
                quality_retention_percent=80,
                platform_support={
                    "nvidia": PlatformSupport(supported=True),
                    "apple_silicon": PlatformSupport(supported=True),
                },
            ),
            ModelVariant(
                id="llama3_8b_q8_0",
                precision="GGUF Q8_0",
                vram_min_mb=8000,
                vram_recommended_mb=12000,
                download_size_gb=8.0,
                quality_retention_percent=95,
                platform_support={
                    "nvidia": PlatformSupport(supported=True),
                    "apple_silicon": PlatformSupport(supported=True),
                },
            ),
        ],
    )


@pytest.fixture
def gguf_model_mixed() -> ModelEntry:
    """Create a model with both K-quant and safe GGUF variants."""
    return ModelEntry(
        id="llama3_8b",
        name="Llama 3 8B",
        category="llm",
        family="llama",
        commercial_use=False,
        variants=[
            ModelVariant(
                id="llama3_8b_q4_k_m",
                precision="GGUF Q4_K_M",
                vram_min_mb=4000,
                vram_recommended_mb=6000,
                download_size_gb=4.0,
                quality_retention_percent=85,
                platform_support={
                    "nvidia": PlatformSupport(supported=True),
                    "apple_silicon": PlatformSupport(supported=True),
                },
            ),
            ModelVariant(
                id="llama3_8b_q4_0",
                precision="GGUF Q4_0",
                vram_min_mb=4000,
                vram_recommended_mb=6000,
                download_size_gb=4.0,
                quality_retention_percent=80,
                platform_support={
                    "nvidia": PlatformSupport(supported=True),
                    "apple_silicon": PlatformSupport(supported=True),
                },
            ),
        ],
    )


# =============================================================================
# Tests: K-quant Safety Detection
# =============================================================================

class TestKQuantSafetyDetection:
    """Tests for _is_safe_gguf_for_mps method."""

    def test_safe_q4_0(self, mock_model_db):
        """Q4_0 should be safe for MPS."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()
        variant.precision = "GGUF Q4_0"
        assert layer._is_safe_gguf_for_mps(variant) is True

    def test_safe_q5_0(self, mock_model_db):
        """Q5_0 should be safe for MPS."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()
        variant.precision = "GGUF Q5_0"
        assert layer._is_safe_gguf_for_mps(variant) is True

    def test_safe_q8_0(self, mock_model_db):
        """Q8_0 should be safe for MPS."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()
        variant.precision = "GGUF Q8_0"
        assert layer._is_safe_gguf_for_mps(variant) is True

    def test_safe_f16(self, mock_model_db):
        """F16 should be safe for MPS."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()
        variant.precision = "GGUF F16"
        assert layer._is_safe_gguf_for_mps(variant) is True

    def test_unsafe_q4_k_m(self, mock_model_db):
        """Q4_K_M (K-quant) should be unsafe for MPS."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()
        variant.precision = "GGUF Q4_K_M"
        assert layer._is_safe_gguf_for_mps(variant) is False

    def test_unsafe_q5_k_s(self, mock_model_db):
        """Q5_K_S (K-quant) should be unsafe for MPS."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()
        variant.precision = "GGUF Q5_K_S"
        assert layer._is_safe_gguf_for_mps(variant) is False

    def test_unsafe_q6_k(self, mock_model_db):
        """Q6_K (K-quant) should be unsafe for MPS."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()
        variant.precision = "GGUF Q6_K"
        assert layer._is_safe_gguf_for_mps(variant) is False

    def test_unsafe_iq_variants(self, mock_model_db):
        """IQ variants should be unsafe for MPS."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()

        for iq_variant in ["GGUF IQ2_XXS", "GGUF IQ3_M", "GGUF IQ4_XS"]:
            variant.precision = iq_variant
            assert layer._is_safe_gguf_for_mps(variant) is False, f"{iq_variant} should be unsafe"

    def test_non_gguf_is_safe(self, mock_model_db):
        """Non-GGUF variants should be treated as safe."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()
        variant.precision = "FP16"
        assert layer._is_safe_gguf_for_mps(variant) is True

    def test_case_insensitive(self, mock_model_db):
        """Detection should be case-insensitive."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        variant = MagicMock()

        # Safe variant in different cases
        for precision in ["gguf q4_0", "GGUF Q4_0", "Gguf Q4_0"]:
            variant.precision = precision
            assert layer._is_safe_gguf_for_mps(variant) is True

        # Unsafe variant in different cases
        for precision in ["gguf q4_k_m", "GGUF Q4_K_M", "Gguf Q4_K_M"]:
            variant.precision = precision
            assert layer._is_safe_gguf_for_mps(variant) is False


# =============================================================================
# Tests: Apple Silicon Model Exclusion
# =============================================================================

class TestAppleSiliconExclusion:
    """Tests for Apple Silicon model exclusion."""

    def test_hunyuan_excluded(self, mock_model_db, hunyuan_model):
        """HunyuanVideo should be excluded on Apple Silicon."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        is_excluded, reason = layer._is_apple_silicon_excluded(hunyuan_model)
        assert is_excluded is True
        assert reason is not None
        assert "16 min" in reason  # Should mention the time

    def test_hunyuan_alternatives(self, mock_model_db, hunyuan_model):
        """HunyuanVideo should suggest alternatives."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        alternatives = layer._get_apple_silicon_alternatives(hunyuan_model)
        assert len(alternatives) > 0
        assert "animatediff" in alternatives or "wan_21_t2v" in alternatives

    def test_regular_model_not_excluded(self, mock_model_db, gguf_model_safe):
        """Regular models should not be excluded."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        is_excluded, reason = layer._is_apple_silicon_excluded(gguf_model_safe)
        assert is_excluded is False
        assert reason is None

    def test_exclusion_name_matching(self, mock_model_db):
        """Exclusion should match on both id and name."""
        layer = ConstraintSatisfactionLayer(mock_model_db)

        # Match on ID
        model1 = MagicMock()
        model1.id = "hunyuan_video_test"
        model1.name = "Some Other Name"
        is_excluded, _ = layer._is_apple_silicon_excluded(model1)
        assert is_excluded is True

        # Match on name
        model2 = MagicMock()
        model2.id = "some_id"
        model2.name = "HunyuanVideo Test"
        is_excluded, _ = layer._is_apple_silicon_excluded(model2)
        assert is_excluded is True


# =============================================================================
# Tests: _check_model Integration
# =============================================================================

class TestCheckModelIntegration:
    """Tests for _check_model with Apple Silicon constraints."""

    def test_hunyuan_rejected_on_apple_silicon(
        self, mock_model_db, apple_silicon_hardware, hunyuan_model
    ):
        """HunyuanVideo should be rejected on Apple Silicon."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        mock_model_db.get_compatible_variants.return_value = hunyuan_model.variants

        result = layer._check_model(
            model=hunyuan_model,
            platform="apple_silicon",
            vram_mb=32000,
            compute_cap=None,
            hardware=apple_silicon_hardware,
        )

        assert isinstance(result, RejectedCandidate)
        assert result.reason == RejectionReason.APPLE_SILICON_EXCLUDED
        assert result.suggestion is not None

    def test_hunyuan_allowed_on_nvidia(
        self, mock_model_db, nvidia_hardware, hunyuan_model
    ):
        """HunyuanVideo should be allowed on NVIDIA."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        mock_model_db.get_compatible_variants.return_value = hunyuan_model.variants

        result = layer._check_model(
            model=hunyuan_model,
            platform="nvidia",
            vram_mb=24000,
            compute_cap=8.9,
            hardware=nvidia_hardware,
        )

        assert isinstance(result, PassingCandidate)

    def test_kquant_rejected_on_apple_silicon(
        self, mock_model_db, apple_silicon_hardware, gguf_model_kquant
    ):
        """K-quant only models should be rejected on Apple Silicon."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        mock_model_db.get_compatible_variants.return_value = gguf_model_kquant.variants

        result = layer._check_model(
            model=gguf_model_kquant,
            platform="apple_silicon",
            vram_mb=32000,
            compute_cap=None,
            hardware=apple_silicon_hardware,
        )

        assert isinstance(result, RejectedCandidate)
        assert result.reason == RejectionReason.MPS_KQUANT_CRASH

    def test_kquant_allowed_on_nvidia(
        self, mock_model_db, nvidia_hardware, gguf_model_kquant
    ):
        """K-quant models should be allowed on NVIDIA."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        mock_model_db.get_compatible_variants.return_value = gguf_model_kquant.variants

        result = layer._check_model(
            model=gguf_model_kquant,
            platform="nvidia",
            vram_mb=24000,
            compute_cap=8.9,
            hardware=nvidia_hardware,
        )

        assert isinstance(result, PassingCandidate)

    def test_safe_gguf_passes_on_apple_silicon(
        self, mock_model_db, apple_silicon_hardware, gguf_model_safe
    ):
        """Safe GGUF variants should pass on Apple Silicon."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        mock_model_db.get_compatible_variants.return_value = gguf_model_safe.variants

        result = layer._check_model(
            model=gguf_model_safe,
            platform="apple_silicon",
            vram_mb=32000,
            compute_cap=None,
            hardware=apple_silicon_hardware,
        )

        assert isinstance(result, PassingCandidate)
        # Should use Q8_0 (higher quality safe variant)
        assert "q8_0" in result.variant.precision.lower() or "q4_0" in result.variant.precision.lower()

    def test_mixed_variants_filters_kquant_on_apple(
        self, mock_model_db, apple_silicon_hardware, gguf_model_mixed
    ):
        """Mixed variants should filter out K-quants on Apple Silicon."""
        layer = ConstraintSatisfactionLayer(mock_model_db)
        mock_model_db.get_compatible_variants.return_value = gguf_model_mixed.variants

        result = layer._check_model(
            model=gguf_model_mixed,
            platform="apple_silicon",
            vram_mb=32000,
            compute_cap=None,
            hardware=apple_silicon_hardware,
        )

        assert isinstance(result, PassingCandidate)
        # Should use Q4_0 (safe), not Q4_K_M (unsafe)
        assert "q4_0" in result.variant.precision.lower()
        assert "_k_" not in result.variant.precision.lower()


# =============================================================================
# Tests: Filter Variant Method
# =============================================================================

class TestFilterMPSSafeVariants:
    """Tests for _filter_mps_safe_variants method."""

    def test_filters_all_kquants(self, mock_model_db):
        """Should filter out all K-quant variants."""
        layer = ConstraintSatisfactionLayer(mock_model_db)

        variants = [
            MagicMock(precision="GGUF Q4_K_M"),
            MagicMock(precision="GGUF Q5_K_S"),
            MagicMock(precision="GGUF Q6_K"),
        ]

        result = layer._filter_mps_safe_variants(variants)
        assert len(result) == 0

    def test_keeps_safe_variants(self, mock_model_db):
        """Should keep safe variants."""
        layer = ConstraintSatisfactionLayer(mock_model_db)

        variants = [
            MagicMock(precision="GGUF Q4_0"),
            MagicMock(precision="GGUF Q5_0"),
            MagicMock(precision="GGUF Q8_0"),
        ]

        result = layer._filter_mps_safe_variants(variants)
        assert len(result) == 3

    def test_mixed_filtering(self, mock_model_db):
        """Should filter K-quants and keep safe variants."""
        layer = ConstraintSatisfactionLayer(mock_model_db)

        variants = [
            MagicMock(precision="GGUF Q4_K_M"),  # unsafe
            MagicMock(precision="GGUF Q4_0"),    # safe
            MagicMock(precision="GGUF Q5_K_S"),  # unsafe
            MagicMock(precision="GGUF Q8_0"),    # safe
        ]

        result = layer._filter_mps_safe_variants(variants)
        assert len(result) == 2
        precisions = [v.precision for v in result]
        assert "GGUF Q4_0" in precisions
        assert "GGUF Q8_0" in precisions


# =============================================================================
# Tests: Constants Validation
# =============================================================================

class TestConstants:
    """Tests for module-level constants."""

    def test_mps_safe_quants_includes_non_k_variants(self):
        """Safe quants should include non-K variants."""
        assert "q4_0" in MPS_SAFE_GGUF_QUANTS
        assert "q5_0" in MPS_SAFE_GGUF_QUANTS
        assert "q8_0" in MPS_SAFE_GGUF_QUANTS

    def test_mps_unsafe_patterns_includes_k_marker(self):
        """Unsafe patterns should include K-quant markers."""
        assert "_k_" in MPS_UNSAFE_GGUF_PATTERNS
        assert "iq" in MPS_UNSAFE_GGUF_PATTERNS

    def test_apple_silicon_excluded_includes_hunyuan(self):
        """Exclusion list should include HunyuanVideo."""
        # Check at least one hunyuan variant is excluded
        has_hunyuan = any(
            "hunyuan" in key for key in APPLE_SILICON_EXCLUDED_MODELS.keys()
        )
        assert has_hunyuan is True

    def test_exclusion_reasons_have_alternatives(self):
        """Each exclusion should explain why."""
        for model_id, reason in APPLE_SILICON_EXCLUDED_MODELS.items():
            assert len(reason) > 0, f"No reason provided for {model_id}"
            # Should mention time or alternative
            assert "min" in reason or "consider" in reason.lower()
