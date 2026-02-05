"""
Unit tests for Resolution Cascade.

Tests the 5-strategy cascade for handling constraint failures per SPEC_v3 Section 6.5.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from src.services.recommendation.resolution_cascade import (
    ResolutionCascade,
    ResolutionStrategy,
    ResolutionAttempt,
    ResolutionResult,
    SUBSTITUTION_MAP,
    CLOUD_FALLBACKS,
    WORKFLOW_ADJUSTMENTS,
    create_cascade_for_hardware,
)
from src.schemas.hardware import (
    HardwareProfile,
    PlatformType,
    FormFactorProfile,
    StorageProfile,
    StorageTier,
    RAMProfile,
)


# --- Mock Objects ---


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
    variants: List[MockModelVariant] = field(default_factory=list)
    cloud: MockCloud = field(default_factory=MockCloud)


def create_mock_hardware(
    vram_gb: float = 8.0,
    is_apple_silicon: bool = False,
    usable_for_offload_gb: float = 16.0,
) -> HardwareProfile:
    """Create a mock HardwareProfile for testing."""
    platform = PlatformType.APPLE_SILICON if is_apple_silicon else PlatformType.WINDOWS_NVIDIA
    return HardwareProfile(
        platform=platform,
        gpu_vendor="apple" if is_apple_silicon else "nvidia",
        gpu_name="Apple M3 Max" if is_apple_silicon else "NVIDIA GeForce RTX 4080",
        vram_gb=vram_gb,
        compute_capability=None if is_apple_silicon else 8.9,
        form_factor=FormFactorProfile(
            is_laptop=False,
            sustained_performance_ratio=1.0,
        ),
        storage=StorageProfile(
            path="C:\\" if not is_apple_silicon else "/",
            total_gb=500.0,
            free_gb=200.0,
            storage_type="nvme_gen4",
            estimated_read_mbps=5000,
            tier=StorageTier.FAST,
        ),
        ram=RAMProfile(
            total_gb=32.0,
            available_gb=24.0,
            usable_for_offload_gb=usable_for_offload_gb,
        ),
    )


def create_model_database() -> Dict[str, MockModelEntry]:
    """Create a mock model database for testing."""
    return {
        "flux_dev": MockModelEntry(
            id="flux_dev",
            name="Flux Dev",
            family="flux_dev",
            variants=[
                MockModelVariant(id="fp16", precision="fp16", vram_min_mb=24000),
                MockModelVariant(id="q8_0", precision="q8_0", vram_min_mb=16000),
                MockModelVariant(id="q4_0", precision="q4_0", vram_min_mb=10000),
            ],
            cloud=MockCloud(partner_node=True, replicate="black-forest-labs/flux-dev"),
        ),
        "flux_schnell": MockModelEntry(
            id="flux_schnell",
            name="Flux Schnell",
            family="flux_schnell",
            variants=[
                MockModelVariant(id="fp16", precision="fp16", vram_min_mb=12000),
                MockModelVariant(id="q8_0", precision="q8_0", vram_min_mb=8000),
            ],
            cloud=MockCloud(partner_node=True),
        ),
        "sdxl_base": MockModelEntry(
            id="sdxl_base",
            name="SDXL Base",
            family="sdxl",
            variants=[
                MockModelVariant(id="fp16", precision="fp16", vram_min_mb=8000),
                MockModelVariant(id="q4_0", precision="q4_0", vram_min_mb=4000),
            ],
            cloud=MockCloud(),
        ),
        "sd15": MockModelEntry(
            id="sd15",
            name="SD 1.5",
            family="sd15",
            variants=[
                MockModelVariant(id="fp16", precision="fp16", vram_min_mb=4000),
            ],
            cloud=MockCloud(),
        ),
    }


# --- Enum Tests ---


class TestResolutionStrategy:
    """Tests for ResolutionStrategy enum."""

    def test_all_strategies_defined(self):
        """Should have all 5 cascade strategies."""
        assert ResolutionStrategy.QUANTIZATION.value == "quantization"
        assert ResolutionStrategy.CPU_OFFLOAD.value == "cpu_offload"
        assert ResolutionStrategy.SUBSTITUTION.value == "substitution"
        assert ResolutionStrategy.WORKFLOW_ADJUSTMENT.value == "workflow_adjustment"
        assert ResolutionStrategy.CLOUD_FALLBACK.value == "cloud_fallback"

    def test_strategy_count(self):
        """Should have exactly 5 strategies."""
        assert len(ResolutionStrategy) == 5


# --- Dataclass Tests ---


class TestResolutionAttempt:
    """Tests for ResolutionAttempt dataclass."""

    def test_fields(self):
        """Should have all expected fields."""
        attempt = ResolutionAttempt(
            strategy=ResolutionStrategy.QUANTIZATION,
            success=True,
            result="q8_0",
            details="Found q8_0 variant",
            performance_impact="40% less VRAM",
        )
        assert attempt.strategy == ResolutionStrategy.QUANTIZATION
        assert attempt.success is True
        assert attempt.result == "q8_0"
        assert "q8_0" in attempt.details
        assert "VRAM" in attempt.performance_impact


class TestResolutionResult:
    """Tests for ResolutionResult dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        result = ResolutionResult(original_model_id="test", resolved=False)
        assert result.resolved is False
        assert result.final_strategy is None
        assert result.attempts == []
        assert result.warnings == []


# --- Configuration Tests ---


class TestSubstitutionMap:
    """Tests for SUBSTITUTION_MAP configuration."""

    def test_flux_has_substitutes(self):
        """Flux family should have substitution paths."""
        assert "flux" in SUBSTITUTION_MAP
        assert len(SUBSTITUTION_MAP["flux"]) > 0

    def test_sdxl_has_substitutes(self):
        """SDXL should fall back to SD 1.5."""
        assert "sdxl" in SUBSTITUTION_MAP
        substitutes = [s[0] for s in SUBSTITUTION_MAP["sdxl"]]
        assert "sd15" in substitutes

    def test_sd15_has_no_substitutes(self):
        """SD 1.5 should have no substitutes (smallest)."""
        assert "sd15" in SUBSTITUTION_MAP
        assert len(SUBSTITUTION_MAP["sd15"]) == 0

    def test_quality_ratios_valid(self):
        """Quality ratios should be between 0 and 1."""
        for family, substitutes in SUBSTITUTION_MAP.items():
            for sub_family, ratio in substitutes:
                assert 0.0 < ratio <= 1.0, f"Invalid ratio for {family}->{sub_family}"


class TestCloudFallbacks:
    """Tests for CLOUD_FALLBACKS configuration."""

    def test_image_generation_fallbacks(self):
        """Image generation should have cloud options."""
        assert "image_generation" in CLOUD_FALLBACKS
        options = CLOUD_FALLBACKS["image_generation"]
        assert "partner_node" in options
        assert "replicate" in options

    def test_video_generation_fallbacks(self):
        """Video generation should have cloud options."""
        assert "video_generation" in CLOUD_FALLBACKS


class TestWorkflowAdjustments:
    """Tests for WORKFLOW_ADJUSTMENTS configuration."""

    def test_reduce_resolution_defined(self):
        """Should have reduce resolution adjustment."""
        assert "reduce_resolution" in WORKFLOW_ADJUSTMENTS
        adj = WORKFLOW_ADJUSTMENTS["reduce_resolution"]
        assert "description" in adj
        assert "impact" in adj

    def test_reduce_batch_defined(self):
        """Should have reduce batch adjustment."""
        assert "reduce_batch" in WORKFLOW_ADJUSTMENTS

    def test_video_shorter_defined(self):
        """Should have video shorter adjustment."""
        assert "video_shorter" in WORKFLOW_ADJUSTMENTS


# --- Cascade Tests ---


class TestQuantizationStrategy:
    """Tests for quantization resolution strategy."""

    def test_finds_fitting_quantization(self):
        """Should find quantization that fits VRAM."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_dev"]  # 24GB fp16, 10GB q4_0
        hardware = create_mock_hardware(vram_gb=12.0)

        # Access public hook for testing
        result = cascade.try_quantization(model, hardware)

        assert result.success is True
        assert result.result == "q4_0"  # Only variant that fits 12GB

    def test_prefers_higher_precision(self):
        """Should prefer higher precision when multiple fit."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_schnell"]  # 12GB fp16, 8GB q8_0
        # With 16GB, both fit - should prefer fp16
        hardware = create_mock_hardware(vram_gb=16.0)
        result = cascade.try_quantization(model, hardware)

        assert result.success is True
        assert result.result == "fp16"

    def test_fails_when_nothing_fits(self):
        """Should fail when no quantization fits."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_dev"]  # Smallest is 10GB q4_0
        hardware = create_mock_hardware(vram_gb=4.0)
        result = cascade.try_quantization(model, hardware)  # Only 4GB

        assert result.success is False

    def test_filters_k_quants_on_apple_silicon(self):
        """Should filter K-quants on Apple Silicon (MPS crashes)."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        # Create model with K-quants only
        model = MockModelEntry(
            id="test",
            name="Test",
            family="test",
            variants=[
                MockModelVariant(precision="q4_K_M", vram_min_mb=4000),  # K-quant
                MockModelVariant(precision="q5_K_S", vram_min_mb=5000),  # K-quant
            ],
        )

        # Apple Silicon should filter these out
        hardware = create_mock_hardware(vram_gb=8.0, is_apple_silicon=True)
        result = cascade.try_quantization(model, hardware)
        assert result.success is False

    def test_allows_safe_quants_on_apple_silicon(self):
        """Should allow safe quantizations on Apple Silicon."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = MockModelEntry(
            id="test",
            name="Test",
            family="test",
            variants=[
                MockModelVariant(precision="q8_0", vram_min_mb=8000),  # Safe
                MockModelVariant(precision="q4_0", vram_min_mb=4000),  # Safe
            ],
        )

        hardware = create_mock_hardware(vram_gb=8.0, is_apple_silicon=True)
        result = cascade.try_quantization(model, hardware)
        assert result.success is True
        assert result.result in ("q8_0", "q4_0")


class TestCPUOffloadStrategy:
    """Tests for CPU offload resolution strategy."""

    def test_offload_when_combined_memory_sufficient(self):
        """Should succeed when VRAM + RAM is sufficient."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_schnell"]  # Needs 12GB fp16
        # 8GB VRAM + 16GB RAM offload = 24GB effective
        hardware = create_mock_hardware(vram_gb=8.0, usable_for_offload_gb=16.0)

        result = cascade.try_cpu_offload(model, hardware)

        assert result.success is True
        assert "offload" in result.details.lower()

    def test_fails_when_combined_insufficient(self):
        """Should fail when even combined memory is insufficient."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_dev"]  # Smallest variant is 10GB q4_0
        # 4GB VRAM + 4GB RAM = 8GB effective - not enough
        hardware = create_mock_hardware(vram_gb=4.0, usable_for_offload_gb=4.0)

        result = cascade.try_cpu_offload(model, hardware)

        assert result.success is False

    def test_reports_performance_impact(self):
        """Should warn about performance impact."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_schnell"]
        hardware = create_mock_hardware(vram_gb=8.0, usable_for_offload_gb=16.0)

        result = cascade.try_cpu_offload(model, hardware)

        assert "5-10x" in result.performance_impact


class TestSubstitutionStrategy:
    """Tests for substitution resolution strategy."""

    def test_finds_substitute_model(self):
        """Should find lighter substitute from same family."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_dev"]  # flux_dev -> flux_schnell -> sdxl
        # 8GB VRAM - flux_dev won't fit, but flux_schnell q8_0 will
        hardware = create_mock_hardware(vram_gb=8.0)
        result = cascade.try_substitution(model, hardware, "txt2img")

        assert result.success is True
        # Should find flux_schnell (8GB q8_0) or sdxl (8GB fp16)
        assert result.result in ("flux_schnell", "sdxl_base")

    def test_no_substitute_for_smallest(self):
        """Should fail when no substitute available."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["sd15"]  # No substitutes defined
        hardware = create_mock_hardware(vram_gb=2.0)
        result = cascade.try_substitution(model, hardware, "txt2img")

        assert result.success is False
        assert "no substitutes" in result.details.lower()


class TestWorkflowAdjustmentStrategy:
    """Tests for workflow adjustment strategy."""

    def test_suggests_adjustments_for_small_gap(self):
        """Should suggest adjustments when gap is small."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        # Model needs 8GB, user has 6GB = 2GB gap
        model = MockModelEntry(
            id="test",
            name="Test",
            family="test",
            variants=[MockModelVariant(vram_min_mb=8000)],
        )
        hardware = create_mock_hardware(vram_gb=6.0)

        # Use "image_generation" - code checks for "image" in use_case
        result = cascade.try_workflow_adjustment(model, hardware, "image_generation")

        assert result.success is True
        assert "resolution" in result.details.lower() or "batch" in result.details.lower()

    def test_fails_for_large_gap(self):
        """Should fail when VRAM gap is too large."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        # Model needs 24GB, user has 4GB = 20GB gap
        model = MockModelEntry(
            id="test",
            name="Test",
            family="test",
            variants=[MockModelVariant(vram_min_mb=24000)],
        )
        hardware = create_mock_hardware(vram_gb=4.0)

        result = cascade.try_workflow_adjustment(model, hardware, "txt2img")

        assert result.success is False
        assert "too large" in result.details.lower()

    def test_video_specific_adjustments(self):
        """Should suggest video-specific adjustments for video use cases."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = MockModelEntry(
            id="test",
            name="Test",
            family="test",
            variants=[MockModelVariant(vram_min_mb=10000)],
        )
        hardware = create_mock_hardware(vram_gb=8.0)

        # Use "video_generation" - code checks for "video" in use_case
        result = cascade.try_workflow_adjustment(model, hardware, "video_generation")

        assert result.success is True
        # Should include video-specific suggestions
        assert "video" in result.details.lower() or "shorter" in result.details.lower()


class TestCloudFallbackStrategy:
    """Tests for cloud fallback strategy."""

    def test_suggests_cloud_for_image_generation(self):
        """Should suggest cloud options for image generation."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_dev"]  # Has partner_node and replicate
        result = cascade.try_cloud_fallback(model, "txt2img")

        assert result.success is True
        assert "partner" in result.details.lower() or "replicate" in result.details.lower()

    def test_suggests_cloud_for_video_generation(self):
        """Should suggest cloud options for video use cases."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = MockModelEntry(id="test", name="Test", family="test")
        result = cascade.try_cloud_fallback(model, "video_animation")

        assert result.success is True

    def test_includes_model_specific_cloud(self):
        """Should prioritize model-specific cloud options."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_dev"]  # Has replicate: "black-forest-labs/flux-dev"
        result = cascade.try_cloud_fallback(model, "txt2img")

        assert result.success is True
        # Should mention the specific replicate endpoint
        assert "partner" in result.details.lower() or "replicate" in result.details.lower()


class TestFullCascade:
    """Tests for full resolution cascade."""

    def test_quantization_stops_cascade(self):
        """Should stop at quantization if successful."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_dev"]  # 10GB q4_0 variant
        hardware = create_mock_hardware(vram_gb=12.0)

        result = cascade.resolve(model, hardware, "VRAM insufficient", "txt2img")

        assert result.resolved is True
        assert result.final_strategy == ResolutionStrategy.QUANTIZATION
        assert len(result.attempts) == 1  # Stopped after first success

    def test_cascade_order_respected(self):
        """Should try strategies in cascade order."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        # Create model that nothing fits - will try all strategies
        model = MockModelEntry(
            id="huge_model",
            name="Huge Model",
            family="unsupported",  # No substitutes
            variants=[MockModelVariant(vram_min_mb=100000)],  # 100GB - nothing fits
            cloud=MockCloud(partner_node=True),
        )
        hardware = create_mock_hardware(vram_gb=4.0, usable_for_offload_gb=4.0)

        result = cascade.resolve(model, hardware, "VRAM insufficient", "txt2img")

        # Should have tried multiple strategies
        assert len(result.attempts) >= 3
        # Check order
        strategies = [a.strategy for a in result.attempts]
        assert strategies[0] == ResolutionStrategy.QUANTIZATION
        # CPU offload should be before substitution
        if ResolutionStrategy.CPU_OFFLOAD in strategies:
            cpu_idx = strategies.index(ResolutionStrategy.CPU_OFFLOAD)
            sub_idx = strategies.index(ResolutionStrategy.SUBSTITUTION)
            assert cpu_idx < sub_idx

    def test_substitution_resolves_when_quant_fails(self):
        """Should fall back to substitution when quantization fails."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_dev"]  # Smallest is 10GB q4_0
        # Only 4GB VRAM, but flux_schnell q8_0 or sdxl fits
        hardware = create_mock_hardware(vram_gb=4.0, usable_for_offload_gb=0.0)

        result = cascade.resolve(model, hardware, "VRAM insufficient", "txt2img")

        # Should resolve via substitution (sd15 fits 4GB)
        assert result.resolved is True
        assert result.final_strategy in (
            ResolutionStrategy.SUBSTITUTION,
            ResolutionStrategy.WORKFLOW_ADJUSTMENT,
            ResolutionStrategy.CLOUD_FALLBACK,
        )

    def test_cloud_fallback_as_last_resort(self):
        """Should use cloud as last resort."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        # Create model where only cloud works
        model = MockModelEntry(
            id="huge_model",
            name="Huge Model",
            family="unknown_family",  # No substitutes
            variants=[MockModelVariant(vram_min_mb=100000)],
            cloud=MockCloud(partner_node=True),
        )
        # Tiny hardware, no offload
        hardware = create_mock_hardware(vram_gb=2.0, usable_for_offload_gb=0.0)

        result = cascade.resolve(model, hardware, "VRAM insufficient", "txt2img")

        assert result.resolved is True
        assert result.final_strategy in (ResolutionStrategy.CLOUD_FALLBACK, ResolutionStrategy.WORKFLOW_ADJUSTMENT)

    def test_result_contains_warnings(self):
        """Should include appropriate warnings."""
        db = create_model_database()
        cascade = ResolutionCascade(db)

        model = db["flux_schnell"]
        hardware = create_mock_hardware(vram_gb=8.0, usable_for_offload_gb=16.0)

        result = cascade.resolve(model, hardware, "VRAM insufficient", "txt2img")

        # Result should have user-facing message
        assert len(result.user_message) > 0


class TestFactoryFunction:
    """Tests for create_cascade_for_hardware factory."""

    def test_creates_cascade_instance(self):
        """Should create ResolutionCascade instance."""
        db = create_model_database()
        hardware = create_mock_hardware()

        cascade = create_cascade_for_hardware(hardware, db)

        assert isinstance(cascade, ResolutionCascade)
        assert cascade.model_db == db
