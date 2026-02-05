"""
Model Database Service.

Loads and queries the models_database.yaml file which contains all model
definitions with variants, platform support, and capabilities.

This replaces the legacy resources.json model loading.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Iterator
from pathlib import Path
import yaml

from src.utils.logger import log


class ModelDatabaseError(Exception):
    """Base exception for model database errors."""
    pass


# =============================================================================
# Data Classes for YAML Schema
# =============================================================================

@dataclass
class PlatformSupport:
    """Platform support configuration for a model variant."""
    supported: bool = False
    min_compute_capability: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class ModelVariant:
    """A specific variant of a model (e.g., fp16, fp8, gguf_q4)."""
    id: str
    precision: str
    vram_min_mb: int
    vram_recommended_mb: int
    download_size_gb: float
    quality_retention_percent: int = 100
    download_url: Optional[str] = None
    sha256: Optional[str] = None  # SHA256 checksum for download verification
    platform_support: Dict[str, PlatformSupport] = field(default_factory=dict)
    requires_nodes: List[str] = field(default_factory=list)
    notes: Optional[str] = None


@dataclass
class ModelCapabilities:
    """Capabilities and scores for a model."""
    primary: List[str] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)
    features: List[Dict[str, Any]] = field(default_factory=list)
    style_strengths: List[str] = field(default_factory=list)
    controlnet_support: List[str] = field(default_factory=list)

    # Video-specific
    video_modes: List[str] = field(default_factory=list)
    max_duration_seconds: Optional[int] = None
    max_resolution: Optional[str] = None
    audio_support: bool = False

    # Audio-specific
    voice_cloning: bool = False
    voice_clone_sample_seconds: Optional[int] = None
    languages: List[str] = field(default_factory=list)
    preset_voices: Optional[int] = None

    # 3D-specific
    output_formats: List[str] = field(default_factory=list)
    pbr_materials: bool = False


@dataclass
class ModelDependencies:
    """Dependencies for a model."""
    required_nodes: List[Dict[str, Any]] = field(default_factory=list)
    paired_models: List[Dict[str, str]] = field(default_factory=list)
    incompatibilities: List[str] = field(default_factory=list)


@dataclass
class ModelExplanation:
    """Pre-written explanation templates for a model."""
    selected: Optional[str] = None
    rejected_vram: Optional[str] = None
    rejected_platform: Optional[str] = None


@dataclass
class CloudInfo:
    """Cloud availability information."""
    partner_node: bool = False
    partner_service: Optional[str] = None
    replicate: bool = False
    estimated_cost_per_generation: Optional[float] = None


@dataclass
class HardwareInfo:
    """
    Hardware requirements and compatibility per SPEC Section 7.2.

    These values are used by:
    - SpaceConstrainedAdjustment: total_size_gb
    - TOPSIS form factor penalty: compute_intensity
    - ResolutionCascade: supports_cpu_offload, ram_for_offload_gb
    - speed_fit criterion: supports_tensorrt
    - Apple Silicon recommendations: mps_performance_penalty

    Values can be explicitly set in YAML or derived from existing model data.
    """
    total_size_gb: float = 0.0           # Total disk space needed (model + VAE + aux)
    compute_intensity: str = "medium"    # "high", "medium", "low" - affects laptop penalty
    supports_cpu_offload: bool = True    # Can offload layers to RAM
    ram_for_offload_gb: float = 0.0      # RAM needed for full model offload
    supports_tensorrt: bool = False      # TensorRT optimization available
    mps_performance_penalty: float = 1.0 # 0.0-1.0, penalty on Apple Silicon (1.0 = not supported)


@dataclass
class ModelEntry:
    """
    Complete model entry from the database.

    Maps directly to the YAML schema defined in SPEC_v3 Section 7.
    """
    id: str
    name: str
    category: str
    family: str
    release_date: Optional[str] = None
    license: Optional[str] = None
    commercial_use: bool = True
    description: Optional[str] = None
    repository_url: Optional[str] = None

    architecture: Dict[str, Any] = field(default_factory=dict)
    variants: List[ModelVariant] = field(default_factory=list)
    capabilities: ModelCapabilities = field(default_factory=ModelCapabilities)
    dependencies: ModelDependencies = field(default_factory=ModelDependencies)
    explanation: ModelExplanation = field(default_factory=ModelExplanation)
    cloud: CloudInfo = field(default_factory=CloudInfo)
    hardware: HardwareInfo = field(default_factory=HardwareInfo)

    # Cloud-only models (no local variants)
    provider: Optional[str] = None
    pricing: Dict[str, float] = field(default_factory=dict)

    # Source classification (two-tier architecture)
    is_cloud_api: bool = False  # True if from cloud_apis section


# =============================================================================
# Platform Constants
# =============================================================================

PLATFORM_KEYS = {
    "windows_nvidia": ["windows", "nvidia"],
    "mac_mps": ["darwin", "apple", "mps"],
    "linux_rocm": ["linux", "amd", "rocm"],
}


def normalize_platform(gpu_vendor: str, os_platform: str) -> str:
    """
    Convert gpu_vendor and OS to a platform key.

    Args:
        gpu_vendor: "nvidia", "apple", "amd", "none"
        os_platform: "Windows", "Darwin", "Linux"

    Returns:
        Platform key: "windows_nvidia", "mac_mps", "linux_rocm"
    """
    os_lower = os_platform.lower()
    vendor_lower = gpu_vendor.lower()

    if "darwin" in os_lower or "mac" in os_lower:
        return "mac_mps"
    elif "linux" in os_lower:
        if vendor_lower in ("amd", "rocm"):
            return "linux_rocm"
        else:
            return "windows_nvidia"  # Linux + NVIDIA uses same support
    else:
        # Windows
        if vendor_lower == "nvidia":
            return "windows_nvidia"
        elif vendor_lower in ("amd", "rocm"):
            return "linux_rocm"  # Windows AMD similar to Linux ROCm support
        else:
            return "windows_nvidia"  # Default


# =============================================================================
# Model Database Class
# =============================================================================

class ModelDatabase:
    """
    Loads and queries the models_database.yaml file.

    This is the single source of truth for model definitions, replacing
    the legacy resources.json model sections.

    Usage:
        db = ModelDatabase()
        db.load()

        # Get all image generation models
        models = db.get_models_by_category("image_generation")

        # Get models compatible with current platform and VRAM
        candidates = db.get_compatible_models(
            platform="windows_nvidia",
            vram_mb=12000,
            categories=["image_generation", "video_generation"]
        )
    """

    # Default path relative to project root
    DEFAULT_PATH = Path(__file__).parent.parent.parent / "data" / "models_database.yaml"

    # Primary categories in the YAML file (two-tier architecture)
    PRIMARY_CATEGORIES = ["local_models", "cloud_apis"]

    # Subcategories within each primary category
    SUBCATEGORIES = [
        "custom_nodes",
        "image_generation",
        "image_editing",
        "image_interrogation",
        "image_upscaling",
        "controlnet",
        "text_encoders",
        "text_generation",
        "video_generation",
        "audio_generation",
        "3d_generation",
        "lip_sync",
    ]

    # For backwards compatibility
    CATEGORIES = SUBCATEGORIES

    def __init__(self, yaml_path: Optional[Path] = None):
        """
        Initialize the model database.

        Args:
            yaml_path: Optional path to the YAML file. Defaults to data/models_database.yaml
        """
        self.yaml_path = yaml_path or self.DEFAULT_PATH
        self._raw_data: Dict[str, Any] = {}
        self._models: Dict[str, ModelEntry] = {}  # Keyed by model ID
        self._loaded = False

    def load(self) -> bool:
        """
        Load the model database from YAML.

        Returns:
            True if loaded successfully, False otherwise.
        """
        try:
            with open(self.yaml_path, "r", encoding="utf-8") as f:
                self._raw_data = yaml.safe_load(f) or {}

            self._parse_models()
            self._loaded = True
            log.info(f"Loaded {len(self._models)} models from {self.yaml_path}")
            return True

        except FileNotFoundError:
            log.error(f"Model database not found: {self.yaml_path}")
            return False
        except yaml.YAMLError as e:
            log.error(f"Failed to parse model database: {e}")
            return False
        except Exception as e:
            log.error(f"Error loading model database: {e}")
            return False

    def _parse_models(self) -> None:
        """Parse raw YAML data into ModelEntry objects.

        Supports both two-tier structure (local_models/cloud_apis with subcategories)
        and legacy flat structure for backwards compatibility.
        """
        self._models.clear()

        # Check if using new two-tier structure
        # The new structure has "local_models" at top level, or "cloud_apis" with subcategories
        if "local_models" in self._raw_data:
            self._parse_two_tier_structure()
        elif "cloud_apis" in self._raw_data and self._is_two_tier_cloud_apis():
            self._parse_two_tier_structure()
        else:
            # Legacy flat structure
            self._parse_flat_structure()

    def _is_two_tier_cloud_apis(self) -> bool:
        """Check if cloud_apis contains subcategories (new) vs direct models (legacy)."""
        cloud_data = self._raw_data.get("cloud_apis", {})
        if not cloud_data:
            return False

        # Check the first entry - if it's a subcategory name, it's new structure
        # In new structure, values are dicts of models (no 'name' field directly)
        # In legacy structure, values are model dicts (have 'name' field)
        for key, value in cloud_data.items():
            if isinstance(value, dict):
                # If the value has a 'name' field, it's a direct model definition (legacy)
                if "name" in value:
                    return False
                # If the value is a dict of dicts (models), it's a subcategory (new)
                if any(isinstance(v, dict) for v in value.values()):
                    return True
            break

        return False

    def _parse_two_tier_structure(self) -> None:
        """Parse the new two-tier category structure."""
        for primary_cat in self.PRIMARY_CATEGORIES:
            primary_data = self._raw_data.get(primary_cat, {})
            if not isinstance(primary_data, dict):
                continue

            is_cloud = primary_cat == "cloud_apis"

            for subcategory, subcat_data in primary_data.items():
                if not isinstance(subcat_data, dict):
                    continue

                for model_id, model_data in subcat_data.items():
                    if not isinstance(model_data, dict):
                        continue

                    try:
                        entry = self._parse_model_entry(
                            model_id, subcategory, model_data, is_cloud=is_cloud
                        )
                        self._models[model_id] = entry
                    except Exception as e:
                        log.warning(f"Failed to parse model {model_id}: {e}")

    def _parse_flat_structure(self) -> None:
        """Parse legacy flat category structure."""
        # Include cloud_apis for backwards compatibility with legacy structure
        all_categories = self.SUBCATEGORIES + ["cloud_apis"]

        for category in all_categories:
            category_data = self._raw_data.get(category, {})
            if not isinstance(category_data, dict):
                continue

            # Legacy cloud_apis at top level are treated as cloud models
            is_cloud = category == "cloud_apis"

            for model_id, model_data in category_data.items():
                if not isinstance(model_data, dict):
                    continue

                try:
                    entry = self._parse_model_entry(
                        model_id, category, model_data, is_cloud=is_cloud
                    )
                    self._models[model_id] = entry
                except Exception as e:
                    log.warning(f"Failed to parse model {model_id}: {e}")

    def _parse_model_entry(
        self,
        model_id: str,
        category: str,
        data: Dict[str, Any],
        is_cloud: bool = False
    ) -> ModelEntry:
        """Parse a single model entry from YAML data."""

        # Parse variants
        variants = []
        for var_data in data.get("variants", []):
            variant = self._parse_variant(var_data)
            variants.append(variant)

        # Parse capabilities
        caps_data = data.get("capabilities", {})
        capabilities = ModelCapabilities(
            primary=caps_data.get("primary", []),
            scores=caps_data.get("scores", {}),
            features=caps_data.get("features", []),
            style_strengths=caps_data.get("style_strengths", []),
            controlnet_support=caps_data.get("controlnet_support", []),
            video_modes=caps_data.get("video_modes", []),
            max_duration_seconds=caps_data.get("max_duration_seconds"),
            max_resolution=caps_data.get("max_resolution"),
            audio_support=caps_data.get("audio_support", False),
            voice_cloning=caps_data.get("voice_cloning", False),
            voice_clone_sample_seconds=caps_data.get("voice_clone_sample_seconds"),
            languages=caps_data.get("languages", []),
            preset_voices=caps_data.get("preset_voices"),
            output_formats=caps_data.get("output_formats", []),
            pbr_materials=caps_data.get("pbr_materials", False),
        )

        # Parse dependencies
        deps_data = data.get("dependencies", {})
        dependencies = ModelDependencies(
            required_nodes=deps_data.get("required_nodes", []),
            paired_models=deps_data.get("paired_models", []),
            incompatibilities=deps_data.get("incompatibilities", []),
        )

        # Parse explanation templates
        expl_data = data.get("explanation", {})
        explanation = ModelExplanation(
            selected=expl_data.get("selected"),
            rejected_vram=expl_data.get("rejected_vram"),
            rejected_platform=expl_data.get("rejected_platform"),
        )

        # Parse cloud info
        cloud_data = data.get("cloud", {})
        cloud = CloudInfo(
            partner_node=cloud_data.get("partner_node", False),
            partner_service=cloud_data.get("partner_service"),
            replicate=cloud_data.get("replicate", False),
            estimated_cost_per_generation=cloud_data.get("estimated_cost_per_generation"),
        )

        # Parse hardware info (with computed defaults)
        hardware = self._parse_hardware(data, variants)

        # Handle cloud-only models (no variants)
        pricing_data = data.get("pricing", {})

        return ModelEntry(
            id=model_id,
            name=data.get("name", model_id),
            category=category,
            family=data.get("family", "unknown"),
            release_date=data.get("release_date"),
            license=data.get("license"),
            commercial_use=data.get("commercial_use", True),
            description=data.get("description"),
            repository_url=data.get("repository") or data.get("repository_url"),
            architecture=data.get("architecture", {}),
            variants=variants,
            capabilities=capabilities,
            dependencies=dependencies,
            explanation=explanation,
            cloud=cloud,
            hardware=hardware,
            provider=data.get("provider"),
            pricing=pricing_data,
            is_cloud_api=is_cloud,
        )

    def _parse_variant(self, data: Dict[str, Any]) -> ModelVariant:
        """Parse a model variant from YAML data."""

        # Parse platform support
        platform_support = {}
        for platform_key in ["windows_nvidia", "mac_mps", "linux_rocm"]:
            ps_data = data.get("platform_support", {}).get(platform_key, {})
            if isinstance(ps_data, dict):
                platform_support[platform_key] = PlatformSupport(
                    supported=ps_data.get("supported", False),
                    min_compute_capability=ps_data.get("min_compute_capability"),
                    notes=ps_data.get("notes"),
                )
            elif isinstance(ps_data, bool):
                platform_support[platform_key] = PlatformSupport(supported=ps_data)

        return ModelVariant(
            id=data.get("id", "unknown"),
            precision=data.get("precision", "fp16"),
            vram_min_mb=data.get("vram_min_mb", 0),
            vram_recommended_mb=data.get("vram_recommended_mb", 0),
            download_size_gb=data.get("download_size_gb", 0),
            quality_retention_percent=data.get("quality_retention_percent", 100),
            download_url=data.get("download_url"),
            sha256=data.get("sha256"),
            platform_support=platform_support,
            requires_nodes=data.get("requires_nodes", []),
            notes=data.get("notes"),
        )

    def _parse_hardware(
        self,
        data: Dict[str, Any],
        variants: List[ModelVariant]
    ) -> HardwareInfo:
        """
        Parse hardware info with computed defaults.

        Explicit values in YAML override computed defaults.
        Derivation logic per SPEC Section 7.2:
        - total_size_gb: max(variant.download_size_gb) * 1.1 (for VAE/aux)
        - compute_intensity: based on architecture.parameters_b
        - ram_for_offload_gb: max(variant.download_size_gb)
        - mps_performance_penalty: 1.0 if no MPS support, else 0.3-0.5
        - supports_cpu_offload: true for most diffusion models
        - supports_tensorrt: depends on architecture type
        """
        hw_data = data.get("hardware", {})
        arch = data.get("architecture", {})

        # Compute defaults from existing data
        defaults = self._compute_hardware_defaults(arch, variants)

        return HardwareInfo(
            total_size_gb=hw_data.get("total_size_gb", defaults["total_size_gb"]),
            compute_intensity=hw_data.get("compute_intensity", defaults["compute_intensity"]),
            supports_cpu_offload=hw_data.get("supports_cpu_offload", defaults["supports_cpu_offload"]),
            ram_for_offload_gb=hw_data.get("ram_for_offload_gb", defaults["ram_for_offload_gb"]),
            supports_tensorrt=hw_data.get("supports_tensorrt", defaults["supports_tensorrt"]),
            mps_performance_penalty=hw_data.get("mps_performance_penalty", defaults["mps_performance_penalty"]),
        )

    def _compute_hardware_defaults(
        self,
        arch: Dict[str, Any],
        variants: List[ModelVariant]
    ) -> Dict[str, Any]:
        """
        Compute default hardware values from existing model data.

        This avoids magic numbers by deriving values from source data.
        Explicit YAML values can override these defaults.
        """
        # Get max variant size
        max_size = max([v.download_size_gb for v in variants], default=0)

        # Get parameter count for intensity
        params_b = arch.get("parameters_b", 0)
        arch_type = arch.get("type", "").lower()

        # Compute intensity from parameters
        # Thresholds: >=10B = high, >=3B = medium, <3B = low
        if params_b >= 10:
            intensity = "high"
        elif params_b >= 3:
            intensity = "medium"
        else:
            intensity = "low"

        # Check MPS support across variants
        mps_supported = False
        for v in variants:
            mps_ps = v.platform_support.get("mac_mps")
            if mps_ps and mps_ps.supported:
                mps_supported = True
                break

        # MPS penalty: 1.0 if not supported, lower if supported
        # Penalty scale based on architecture complexity
        if not mps_supported:
            mps_penalty = 1.0
        elif "moe" in arch_type:
            mps_penalty = 0.7  # MoE models run slower on MPS
        elif params_b >= 10:
            mps_penalty = 0.5  # Large models have some penalty
        else:
            mps_penalty = 0.3  # Smaller models run well

        # TensorRT support based on architecture
        # Standard UNet and DiT support TensorRT, MoE doesn't
        supports_trt = arch_type in ("unet", "dit", "mmdit", "rectified_flow_transformer")
        if "moe" in arch_type:
            supports_trt = False

        # CPU offload: most diffusion models support it, small models don't need it
        supports_offload = params_b >= 1.0  # Models under 1B don't benefit from offload

        return {
            "total_size_gb": round(max_size * 1.1, 1),  # Add 10% for VAE/aux
            "compute_intensity": intensity,
            "supports_cpu_offload": supports_offload,
            "ram_for_offload_gb": round(max_size, 1),  # Model needs to fit in RAM
            "supports_tensorrt": supports_trt,
            "mps_performance_penalty": mps_penalty,
        }

    # =========================================================================
    # Query Methods
    # =========================================================================

    @property
    def is_loaded(self) -> bool:
        """Check if database is loaded."""
        return self._loaded

    def get_model(self, model_id: str) -> Optional[ModelEntry]:
        """Get a model by ID."""
        return self._models.get(model_id)

    def get_all_models(self) -> List[ModelEntry]:
        """Get all models."""
        return list(self._models.values())

    def get_models_by_category(self, category: str) -> List[ModelEntry]:
        """Get all models in a category."""
        return [m for m in self._models.values() if m.category == category]

    def get_models_by_family(self, family: str) -> List[ModelEntry]:
        """Get all models in a family (e.g., 'flux', 'wan', 'sdxl')."""
        return [m for m in self._models.values() if m.family == family]

    def get_models_by_capability(self, capability: str) -> List[ModelEntry]:
        """Get models that support a specific capability (e.g., 'text_to_image')."""
        return [
            m for m in self._models.values()
            if capability in m.capabilities.primary
        ]

    def get_local_models(self) -> List[ModelEntry]:
        """Get models from the local_models section (run locally on user hardware)."""
        return [m for m in self._models.values() if not m.is_cloud_api]

    def get_cloud_models(self) -> List[ModelEntry]:
        """Get models from the cloud_apis section (cloud-based API models)."""
        return [m for m in self._models.values() if m.is_cloud_api]

    def get_models_with_variants(self) -> List[ModelEntry]:
        """Get all models that have downloadable variants (for backwards compatibility)."""
        return [m for m in self._models.values() if m.variants]

    def get_compatible_variants(
        self,
        model: ModelEntry,
        platform: str,
        vram_mb: int,
        compute_capability: Optional[float] = None,
    ) -> List[ModelVariant]:
        """
        Get variants of a model compatible with the given hardware.

        Args:
            model: The model entry
            platform: Platform key (e.g., "windows_nvidia", "mac_mps")
            vram_mb: Available VRAM in MB
            compute_capability: CUDA compute capability (for FP8 filtering)

        Returns:
            List of compatible variants, sorted by quality retention (highest first)
        """
        compatible = []

        for variant in model.variants:
            # Check VRAM requirement
            if variant.vram_min_mb > vram_mb:
                continue

            # Check platform support
            ps = variant.platform_support.get(platform)
            if not ps or not ps.supported:
                continue

            # Check compute capability for FP8 variants
            if ps.min_compute_capability:
                # If variant requires specific CC but none provided, skip it
                if compute_capability is None:
                    continue
                # If CC provided but too low, skip it
                if compute_capability < ps.min_compute_capability:
                    continue

            # Check MPS K-quant restrictions
            if platform == "mac_mps" and "k_" in variant.precision.lower():
                # K-quants crash on MPS - skip unless explicitly noted as safe
                if not ps.notes or "k-quant" not in ps.notes.lower():
                    continue

            compatible.append(variant)

        # Sort by quality retention (prefer higher quality)
        compatible.sort(key=lambda v: v.quality_retention_percent, reverse=True)

        return compatible

    def get_compatible_models(
        self,
        platform: str,
        vram_mb: int,
        categories: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        compute_capability: Optional[float] = None,
        commercial_only: bool = False,
    ) -> List[tuple[ModelEntry, ModelVariant]]:
        """
        Get all models with at least one compatible variant.

        Args:
            platform: Platform key (e.g., "windows_nvidia", "mac_mps")
            vram_mb: Available VRAM in MB
            categories: Filter to specific categories (None = all)
            capabilities: Filter to models with these capabilities (None = all)
            compute_capability: CUDA compute capability (for FP8 filtering)
            commercial_only: Only include commercially-licensed models

        Returns:
            List of (model, best_variant) tuples
        """
        results = []

        for model in self._models.values():
            # Category filter
            if categories and model.category not in categories:
                continue

            # Capability filter
            if capabilities:
                if not any(c in model.capabilities.primary for c in capabilities):
                    continue

            # Commercial license filter
            if commercial_only and not model.commercial_use:
                continue

            # Get compatible variants
            variants = self.get_compatible_variants(
                model, platform, vram_mb, compute_capability
            )

            if variants:
                # Return best variant (highest quality retention)
                results.append((model, variants[0]))

        return results

    def get_required_nodes(self, model: ModelEntry, variant: ModelVariant) -> List[str]:
        """
        Get all required custom nodes for a model+variant combination.

        Args:
            model: The model entry
            variant: The selected variant

        Returns:
            List of required node package names
        """
        nodes = set()

        # Variant-specific nodes (e.g., ComfyUI-GGUF for GGUF variants)
        nodes.update(variant.requires_nodes)

        # Model-level dependencies
        for dep in model.dependencies.required_nodes:
            if isinstance(dep, dict):
                package = dep.get("package", "")
                required_for = dep.get("required_for", [])

                # Check if this node is required for this variant
                if "all" in required_for or variant.id in required_for:
                    nodes.add(package)
            elif isinstance(dep, str):
                nodes.add(dep)

        return list(nodes)

    def get_paired_models(self, model: ModelEntry) -> List[str]:
        """
        Get model IDs that must be used together with this model.

        Args:
            model: The model entry

        Returns:
            List of paired model IDs
        """
        return [
            pm.get("model_id", "")
            for pm in model.dependencies.paired_models
            if pm.get("model_id")
        ]

    def iter_models(self) -> Iterator[ModelEntry]:
        """Iterate over all models."""
        yield from self._models.values()

    def __len__(self) -> int:
        """Return number of models in database."""
        return len(self._models)

    def __contains__(self, model_id: str) -> bool:
        """Check if a model ID exists."""
        return model_id in self._models


# =============================================================================
# Module-level singleton for convenience
# =============================================================================

_default_database: Optional[ModelDatabase] = None


def get_model_database() -> ModelDatabase:
    """
    Get the default model database instance.

    Loads the database on first call.

    Returns:
        The ModelDatabase singleton instance
    """
    global _default_database

    if _default_database is None:
        _default_database = ModelDatabase()
        _default_database.load()

    return _default_database


def reload_model_database() -> ModelDatabase:
    """
    Reload the model database from disk.

    Returns:
        The reloaded ModelDatabase instance
    """
    global _default_database

    _default_database = ModelDatabase()
    _default_database.load()

    return _default_database


class SQLiteModelDatabase:
    """
    Relational implementation of the Model Database using SQLite.
    Optimized for Task DB-01.
    """
    def __init__(self, db_manager=None):
        from src.services.database.engine import db_manager as default_manager
        from src.services.database.models import Model as DBModel, ModelVariant as DBModelVariant
        self.db_manager = db_manager or default_manager
        self.DBModel = DBModel
        self.DBModelVariant = DBModelVariant

    def get_compatible_models(
        self,
        platform: str,
        vram_mb: int,
        categories: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
        compute_capability: Optional[float] = None,
        commercial_only: bool = False,
    ) -> List[tuple[Any, Any]]:
        """
        Relational implementation of model selection using indexed SQL queries.
        """
        session = self.db_manager.get_session()
        try:
            # Base query joining Models and Variants
            query = session.query(self.DBModel, self.DBModelVariant).join(
                self.DBModelVariant, self.DBModel.id == self.DBModelVariant.model_id
            )

            # 1. Hard Constraints (Layer 1 - CSP equivalent in SQL)
            query = query.filter(self.DBModelVariant.vram_min_mb <= vram_mb)
            
            # 2. Category Filter
            if categories:
                query = query.filter(self.DBModel.category.in_(categories))

            # 3. Commercial Filter
            if commercial_only:
                query = query.filter(self.DBModel.commercial_use == True)

            # Execute and post-process for complex logic (JSON parsing)
            raw_results = query.all()
            log.debug(f"SQL query returned {len(raw_results)} raw rows.")
            
            # Group by Model to pick best variant
            model_best_variant = {}
            
            for model_row, variant_row in raw_results:
                # Platform compatibility check (JSON logic)
                ps = variant_row.platform_support.get(platform, {})
                if not ps.get("supported"):
                    continue
                
                # Compute capability check
                min_cc = ps.get("cc")
                if min_cc and (compute_capability is None or compute_capability < min_cc):
                    continue

                # Best variant selection (Highest quality retention)
                if model_row.id not in model_best_variant:
                    model_best_variant[model_row.id] = (model_row, variant_row)
                else:
                    existing_variant = model_best_variant[model_row.id][1]
                    if variant_row.quality_retention_percent > existing_variant.quality_retention_percent:
                        model_best_variant[model_row.id] = (model_row, variant_row)

            return list(model_best_variant.values())

        finally:
            session.close()
