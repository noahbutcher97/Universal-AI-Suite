"""
Model-related schemas for the AI Universal Suite.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


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
    
    # Package metadata (for CLI/Tools)
    package: Optional[str] = None
    package_type: Optional[str] = None # npm, pip, system
    bin: Optional[str] = None
    api_key_name: Optional[str] = None
    api_key_url: Optional[str] = None


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
