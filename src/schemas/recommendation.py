from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Any, Tuple, Set
from uuid import uuid4
from enum import Enum

from src.schemas.model import ModelEntry, ModelVariant

# --- Modern Recommendation Result Schemas (SPEC_v3 Section 6) ---

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
    model: Optional[ModelEntry] = None  # Full model for explainer access to variants


@dataclass
class PassingCandidate:
    """A model that passed constraint satisfaction."""
    model: ModelEntry
    variant: ModelVariant
    execution_mode: str = "native"  # "native", "quantized", "gpu_offload"
    warnings: List[str] = field(default_factory=list)


@dataclass
class FeatureMatch:
    """A feature that matches between user and model."""
    feature_id: str
    user_value: float
    model_value: float
    contribution: float  # How much this contributed to similarity


@dataclass
class ScoredCandidate:
    """A candidate with content-based similarity score."""
    passing_candidate: PassingCandidate
    similarity_score: float  # 0.0 - 1.0
    matching_features: List[FeatureMatch] = field(default_factory=list)
    style_match_bonus: float = 0.0


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

    # Compatibility Layer properties to support legacy UI
    @property
    def id(self) -> str:
        return self.scored_candidate.passing_candidate.model.id

    @property
    def display_name(self) -> str:
        model = self.scored_candidate.passing_candidate.model
        variant = self.scored_candidate.passing_candidate.variant
        return f"{model.name} ({variant.precision.upper()})"

    @property
    def composite_score(self) -> float:
        return self.closeness_coefficient

    @property
    def reasoning(self) -> List[str]:
        return [self.explanation]

    @property
    def tier(self) -> str:
        # Map to legacy tier names for UI
        vram_min = self.scored_candidate.passing_candidate.variant.vram_min_mb
        if vram_min >= 12000: return "flux"
        if vram_min >= 8000: return "sdxl"
        return "sd15"

    @property
    def category(self) -> str:
        return self.scored_candidate.passing_candidate.model.category

    @property
    def execution_mode(self) -> str:
        return self.scored_candidate.passing_candidate.execution_mode

    @property
    def precision(self) -> str:
        return self.scored_candidate.passing_candidate.variant.precision

    @property
    def capabilities(self):
        # Maps modern capabilities to ModelCapabilityScores-like structure
        return self.scored_candidate.passing_candidate.model.capabilities

    @property
    def requirements(self) -> Dict[str, Any]:
        v = self.scored_candidate.passing_candidate.variant
        return {
            "url": v.download_url,
            "size_gb": v.download_size_gb,
            "vram_min_mb": v.vram_min_mb,
            "vram_recommended_mb": v.vram_recommended_mb,
            "precision": v.precision,
        }

    @property
    def required_nodes(self) -> List[str]:
        # Simple extraction from model+variant
        model = self.scored_candidate.passing_candidate.model
        variant = self.scored_candidate.passing_candidate.variant
        nodes = set(variant.requires_nodes)
        for node in model.dependencies.required_nodes:
            if isinstance(node, str): nodes.add(node)
            elif isinstance(node, dict): nodes.add(node.get("id") or node.get("package", ""))
        return list(nodes)

    @property
    def content_similarity_score(self) -> float:
        return self.criterion_scores.get("content_similarity").raw_score if "content_similarity" in self.criterion_scores else 0.5

    @property
    def hardware_fit_score(self) -> float:
        return self.criterion_scores.get("hardware_fit").raw_score if "hardware_fit" in self.criterion_scores else 0.5

    @property
    def speed_fit_score(self) -> float:
        return self.criterion_scores.get("speed_fit").raw_score if "speed_fit" in self.criterion_scores else 0.5

    @property
    def user_fit_score(self) -> float:
        return self.criterion_scores.get("ecosystem_maturity").raw_score if "ecosystem_maturity" in self.criterion_scores else 0.5

    @property
    def approach_fit_score(self) -> float:
        return self.criterion_scores.get("approach_fit").raw_score if "approach_fit" in self.criterion_scores else 0.5


# --- User Input Schemas ---

@dataclass
class ModelCapabilityScores:
    """
    Comprehensive capability scores for model evaluation (0.0-1.0).
    """
    # Quality
    photorealism: float = 0.5
    artistic_stylization: float = 0.5
    output_fidelity: float = 0.5
    prompt_adherence: float = 0.5
    
    # Speed/Efficiency
    generation_speed: float = 0.5
    vram_efficiency: float = 0.5
    
    # Editing
    holistic_editing: float = 0.0
    localized_editing: float = 0.0
    
    # Video
    motion_subtlety: float = 0.0
    motion_dynamic: float = 0.0
    temporal_coherence: float = 0.0
    
    # Special
    character_consistency: float = 0.0
    pose_control: float = 0.0

@dataclass
class CLICapabilityScores:
    """
    Capabilities for AI CLI providers (0.0-1.0).
    """
    coding: float = 0.0
    creative_writing: float = 0.0
    analysis: float = 0.0
    multimodal: float = 0.0
    local_execution: float = 0.0 # 1.0 = runs locally, 0.0 = cloud only

# --- User Input Schemas ---

@dataclass
class ContentPreferences:
    """Detailed parameters about desired output characteristics."""
    # Output Quality Priorities (1-5)
    photorealism: int = 3
    artistic_stylization: int = 3
    generation_speed: int = 3
    output_quality: int = 3
    consistency: int = 3
    editability: int = 3

    # Domain-Specific
    motion_intensity: Optional[int] = None # 1-5 scale (1=Subtle, 5=Dynamic)
    temporal_coherence: Optional[int] = None
    holistic_edits: Optional[int] = None
    localized_edits: Optional[int] = None
    character_consistency: Optional[int] = None
    pose_control: Optional[int] = None

    # Style & Output
    style_tags: List[str] = field(default_factory=list)
    typical_resolution: str = "1024x1024"
    batch_frequency: int = 3

    # Advanced
    preferred_approach: Optional[str] = None # "minimal", "monolithic", etc.
    quantization_acceptable: bool = True

@dataclass
class CLIPreferences:
    """Preferences for CLI assistant selection."""
    primary_tasks: List[str] = field(default_factory=list) # ["coding", "writing", "research"]
    privacy_sensitivity: int = 3 # 1-5 (5=Local Only)
    cost_sensitivity: int = 3 # 1-5
    context_window_importance: int = 3


# --- Cloud API Preferences (PLAN: Cloud API Integration) ---

@dataclass
class CloudAPIPreferences:
    """
    User's preferences for cloud vs local model execution.

    Per PLAN: Cloud API Integration - these preferences shape whether
    recommendations come from local_models or cloud_apis database sections.

    Attributes:
        cloud_willingness: How the user wants to run AI models
            - "local_only": Only download and run locally (no cloud recommendations)
            - "cloud_fallback": Prefer local, show cloud when hardware can't handle it (DEFAULT)
            - "cloud_preferred": Prefer cloud APIs, show local as alternative
            - "cloud_only": Exclusively use cloud APIs (skip GPU detection)
        cost_sensitivity: How important keeping costs low is (1-5 scale)
            - 1: Budget isn't a concern (quality/speed dominate)
            - 3: Balance of cost and quality (DEFAULT)
            - 5: Minimize cost at all costs (cost dominates, soft filter expensive)
    """
    cloud_willingness: Literal["local_only", "cloud_fallback", "cloud_preferred", "cloud_only"] = "cloud_fallback"
    cost_sensitivity: int = 3  # 1-5 scale


# --- Modular Modality Preferences (SPEC_v3 Section 6.3.1) ---
# These schemas replace the flat ContentPreferences for multi-modal use cases.
# Migration: ContentPreferences -> UseCaseDefinition (see convert_legacy_preferences())

@dataclass
class SharedQualityPrefs:
    """
    Cross-cutting quality preferences that apply across all modalities.

    Per SPEC_v3 Section 6.3.1: These are shared between image, video, audio, etc.
    Scale: 1-5 where 1=Low priority, 5=High priority
    """
    photorealism: int = 3
    artistic_stylization: int = 3
    generation_speed: int = 3
    output_quality: int = 3
    character_consistency: Optional[int] = None  # For character-based workflows


@dataclass
class ImageModalityPrefs:
    """
    Image generation specific preferences.

    Per SPEC_v3 Section 6.3.1: Only included when use case requires image modality.
    Scale: 1-5 where 1=Low priority, 5=High priority
    """
    editability: int = 3
    pose_control: Optional[int] = None
    holistic_edits: Optional[int] = None  # Global image edits (style transfer, etc.)
    localized_edits: Optional[int] = None  # Inpainting, outpainting
    style_tags: List[str] = field(default_factory=list)
    typical_resolution: str = "1024x1024"


@dataclass
class VideoModalityPrefs:
    """
    Video generation specific preferences.

    Per SPEC_v3 Section 6.3.1: Only included when use case requires video modality.
    Scale: 1-5 where 1=Low priority, 5=High priority
    """
    motion_intensity: int = 3  # 1=Subtle/slow, 5=Dynamic/fast
    temporal_coherence: int = 3  # Frame-to-frame consistency
    duration_preference: str = "4s"  # Typical clip duration


@dataclass
class AudioModalityPrefs:
    """
    Audio generation specific preferences (future).

    Per SPEC_v3 Section 6.3.1: Stub for future audio modality support.
    """
    pass  # TODO: Define when audio models are added


@dataclass
class ThreeDModalityPrefs:
    """
    3D generation specific preferences (future).

    Per SPEC_v3 Section 6.3.1: Stub for future 3D modality support.
    """
    pass  # TODO: Define when 3D models are added


@dataclass
class UseCaseDefinition:
    """
    A use case that composes one or more modalities.

    Per SPEC_v3 Section 6.3.1: Use cases can span multiple modalities
    (e.g., character animation = image + video, music video = image + video + audio).

    The recommendation engine scores candidates per modality, then aggregates.
    """
    id: str  # e.g., "character_animation", "txt2img", "music_video"
    name: str  # e.g., "Character Animation Workflow"
    required_modalities: List[str] = field(default_factory=list)  # ["image", "video"]

    # Cross-cutting preferences (always present)
    shared: SharedQualityPrefs = field(default_factory=SharedQualityPrefs)

    # Modality-specific preferences (only populate what's needed)
    image: Optional[ImageModalityPrefs] = None
    video: Optional[VideoModalityPrefs] = None
    audio: Optional[AudioModalityPrefs] = None
    three_d: Optional[ThreeDModalityPrefs] = None

    # Cross-cutting settings
    batch_frequency: int = 3  # How often user generates (1=rarely, 5=constantly)
    preferred_approach: Optional[str] = None  # "minimal", "monolithic", etc.
    quantization_acceptable: bool = True


# --- Use Case Templates ---
# Pre-defined use case configurations for common workflows

USE_CASE_TEMPLATES: Dict[str, UseCaseDefinition] = {
    "txt2img": UseCaseDefinition(
        id="txt2img",
        name="Text to Image",
        required_modalities=["image"],
    ),
    "img2img": UseCaseDefinition(
        id="img2img",
        name="Image to Image",
        required_modalities=["image"],
    ),
    "inpainting": UseCaseDefinition(
        id="inpainting",
        name="Inpainting/Editing",
        required_modalities=["image"],
    ),
    "txt2vid": UseCaseDefinition(
        id="txt2vid",
        name="Text to Video",
        required_modalities=["video"],
    ),
    "img2vid": UseCaseDefinition(
        id="img2vid",
        name="Image to Video",
        required_modalities=["image", "video"],
    ),
    "character_animation": UseCaseDefinition(
        id="character_animation",
        name="Character Animation",
        required_modalities=["image", "video"],
    ),
}


def convert_legacy_preferences(
    use_case_id: str,
    legacy_prefs: "ContentPreferences",
) -> UseCaseDefinition:
    """
    Convert legacy flat ContentPreferences to new UseCaseDefinition.

    Per PLAN_v3.md deprecation tracker: ContentPreferences is deprecated in v1.1,
    removed in v2.0. This function enables gradual migration.

    Args:
        use_case_id: The use case identifier (e.g., "txt2img", "txt2vid")
        legacy_prefs: The old-style flat ContentPreferences

    Returns:
        UseCaseDefinition with modality-specific preferences populated
    """
    # Determine required modalities from use case ID
    modality_map = {
        "txt2img": ["image"],
        "img2img": ["image"],
        "inpainting": ["image"],
        "txt2vid": ["video"],
        "img2vid": ["image", "video"],
        "character_animation": ["image", "video"],
        "flf2v": ["image", "video"],  # First/last frame to video
    }
    required_modalities = modality_map.get(use_case_id, ["image"])

    # Build shared quality preferences
    shared = SharedQualityPrefs(
        photorealism=legacy_prefs.photorealism,
        artistic_stylization=legacy_prefs.artistic_stylization,
        generation_speed=legacy_prefs.generation_speed,
        output_quality=legacy_prefs.output_quality,
        character_consistency=legacy_prefs.character_consistency,
    )

    # Build image preferences if needed
    image_prefs = None
    if "image" in required_modalities:
        image_prefs = ImageModalityPrefs(
            editability=legacy_prefs.editability,
            pose_control=legacy_prefs.pose_control,
            holistic_edits=legacy_prefs.holistic_edits,
            localized_edits=legacy_prefs.localized_edits,
            style_tags=legacy_prefs.style_tags.copy() if legacy_prefs.style_tags else [],
            typical_resolution=legacy_prefs.typical_resolution,
        )

    # Build video preferences if needed
    video_prefs = None
    if "video" in required_modalities:
        video_prefs = VideoModalityPrefs(
            motion_intensity=legacy_prefs.motion_intensity or 3,
            temporal_coherence=legacy_prefs.temporal_coherence or 3,
            duration_preference="4s",  # Default, not in legacy schema
        )

    return UseCaseDefinition(
        id=use_case_id,
        name=USE_CASE_TEMPLATES.get(use_case_id, UseCaseDefinition(id="", name="")).name or use_case_id,
        required_modalities=required_modalities,
        shared=shared,
        image=image_prefs,
        video=video_prefs,
        batch_frequency=legacy_prefs.batch_frequency,
        preferred_approach=legacy_prefs.preferred_approach,
        quantization_acceptable=legacy_prefs.quantization_acceptable,
    )


@dataclass
class UserProfile:
    """User's self-reported experience and preferences."""
    # Experience (1-5)
    ai_experience: int = 1
    technical_experience: int = 1
    proficiency: Literal["Beginner", "Intermediate", "Advanced", "Expert"] = "Beginner"

    # Use Case Intent
    primary_use_cases: List[str] = field(default_factory=list)
    content_preferences: Dict[str, ContentPreferences] = field(default_factory=dict)

    # CLI Specifics
    cli_preferences: Optional[CLIPreferences] = None

    # Cloud API Preferences (PLAN: Cloud API Integration)
    cloud_api_preferences: CloudAPIPreferences = field(default_factory=CloudAPIPreferences)

    # Workflow Preferences (1-5)
    prefer_simple_setup: int = 3
    prefer_local_processing: int = 3  # DEPRECATED: Use cloud_api_preferences.cloud_willingness instead
    prefer_open_source: int = 3

# --- Hardware Schemas ---

@dataclass
class HardwareConstraints:
    """Normalized hardware capabilities scores (0.0 - 1.0)."""
    # Normalized Scores
    vram_score: float = 0.0
    ram_score: float = 0.0
    storage_score: float = 0.0
    compute_score: float = 0.0
    cpu_score: float = 0.0
    memory_bandwidth_score: float = 0.0
    storage_speed_score: float = 0.0
    thermal_headroom_score: float = 0.0

    # Hard Limits
    can_run_flux: bool = False
    can_run_sdxl: bool = False
    can_run_video: bool = False
    requires_quantization: bool = False
    can_sustain_load: bool = False
    storage_adequate: bool = False

    # Derived
    recommended_batch_size: int = 1
    recommended_resolution_cap: str = "1024x1024"
    expected_thermal_throttle: bool = False

    # Raw values for reference
    gpu_vendor: str = "none"
    gpu_name: str = "Unknown"
    vram_gb: float = 0.0
    ram_gb: float = 0.0
    disk_free_gb: float = 0.0

# --- Candidate Schemas ---

@dataclass
class CLICandidate:
    id: str
    display_name: str
    provider: str = "gemini"
    composite_score: float = 0.0
    capabilities: CLICapabilityScores = field(default_factory=CLICapabilityScores)
    requires_api_key: bool = True
    reasoning: List[str] = field(default_factory=list)


# --- Cloud Recommendation Schemas (PLAN: Cloud API Integration) ---

@dataclass
class CloudRankedCandidate:
    """
    A cloud model recommendation with hybrid scoring.

    Per PLAN: Cloud API Integration - Cloud models use a mix of shared criteria
    (same as local) and cloud-specific criteria (replacing hardware_fit).

    Attributes:
        model_id: Unique identifier for the cloud model
        display_name: Human-readable name
        provider: API provider (e.g., "openai", "stability_ai", "comfy_partner_node")

        # Shared criteria scores (same as local pathway, 0.0-1.0)
        content_score: Use case match from modality scorers
        style_score: Aesthetic/approach alignment
        approach_score: Workflow compatibility
        ecosystem_score: Documentation, support, stability

        # Cloud-specific criteria scores (0.0-1.0)
        cost_score: Cost efficiency (inverse of price)
        provider_score: Reliability (Partner Node > Major providers > Others)
        rate_limit_score: Throttling/quota headroom
        latency_score: API response time / generation wait time

        overall_score: TOPSIS-like composite score
        estimated_cost_per_use: Cost per generation (e.g., $0.04/image)
        estimated_monthly_cost: Based on projected usage from batch_frequency
        setup_type: "partner_node" or "api_key"
        storage_boost_applied: True if score was boosted due to storage constraint
    """
    model_id: str
    display_name: str
    provider: str
    category: str = "image_generation"  # For modality filtering in UI

    # Shared criteria scores (same as local)
    content_score: float = 0.0       # Use case match
    style_score: float = 0.0         # Aesthetic/approach fit
    approach_score: float = 0.0      # Workflow compatibility
    ecosystem_score: float = 0.0     # Docs, support, stability

    # Cloud-specific criteria scores
    cost_score: float = 0.0          # Cost efficiency (inverse of price)
    provider_score: float = 0.0      # Reliability (Partner Node bonus)
    rate_limit_score: float = 0.0    # Throttling/quota headroom
    latency_score: float = 0.0       # API response time

    overall_score: float = 0.0       # TOPSIS-like composite
    estimated_cost_per_use: float = 0.0
    estimated_monthly_cost: float = 0.0  # Based on projected usage
    setup_type: Literal["partner_node", "api_key"] = "api_key"
    storage_boost_applied: bool = False  # True if boosted due to storage constraint

    # Explanation
    reasoning: List[str] = field(default_factory=list)


@dataclass
class CloudRecommendationInfo:
    """
    Additional cloud-specific info for display purposes.

    Per PLAN: Cloud API Integration - Attached to recommendations that
    can be fulfilled via cloud APIs.
    """
    is_cloud: bool = False
    provider: str = ""
    partner_node_available: bool = False
    estimated_cost_per_use: float = 0.0
    setup_instructions: str = ""  # URL or inline instructions


@dataclass
class RecommendationResults:
    """
    Combined results from both local and cloud recommendation pathways.

    Per PLAN: Cloud API Integration - Parallel pathways return separate
    recommendation lists. The primary_pathway indicates which should be
    displayed first based on user's cloud_willingness setting.
    """
    local_recommendations: List[RankedCandidate] = field(default_factory=list)
    cloud_recommendations: List[CloudRankedCandidate] = field(default_factory=list)
    primary_pathway: Literal["local", "cloud"] = "local"

    # Storage constraint info
    storage_constrained: bool = False  # True if < 50GB free
    storage_warnings: List[str] = field(default_factory=list)  # Warnings for large local models


# --- Result Schema ---

@dataclass
class ModuleRecommendation:
    """Output of RecommendationService for a single module"""
    
    module_id: str                          # "comfyui"
    enabled: bool                           # Whether to install
    
    # Module-specific config
    config: Dict[str, Any]                  # Varies by module
    
    # For display
    display_name: str
    description: str
    reasoning: List[str]                    # Why this recommendation
    warnings: List[str]                     # Potential issues
    
    # Installation details
    components: List[str]                   # What will be installed
    estimated_size_gb: float
    estimated_time_minutes: int
    
    # User overridable
    optional_features: Dict[str, bool] = field(default_factory=dict)
    advanced_options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RecommendationResult:
    """Complete output of the recommendation engine."""
    recommendation_id: str = field(default_factory=lambda: str(uuid4()))
    confidence_score: float = 0.0
    
    user_profile: UserProfile = None
    hardware_constraints: HardwareConstraints = None
    
    # Selections
    selected_models: Dict[str, RankedCandidate] = field(default_factory=dict) # mapped by use_case
    selected_cli: Optional[CLICandidate] = None
    
    # Installation manifest (The final "To-Do" list)
    manifest: Dict[str, Any] = field(default_factory=dict)
    
    reasoning: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
