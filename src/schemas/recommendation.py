from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Any
from uuid import uuid4

# --- Scoring Primitives ---

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

    # Workflow Preferences (1-5)
    prefer_simple_setup: int = 3
    prefer_local_processing: int = 3
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
class Candidate:
    id: str
    display_name: str
    composite_score: float = 0.0
    rejection_reason: Optional[str] = None
    reasoning: List[str] = field(default_factory=list)

@dataclass
class ModelCandidate(Candidate):
    tier: str = "sd15"
    capabilities: ModelCapabilityScores = field(default_factory=ModelCapabilityScores)
    requirements: Dict[str, Any] = field(default_factory=dict)
    approach: str = "minimal"
    required_nodes: List[str] = field(default_factory=list)
    
    # Intermediate scores
    hardware_fit_score: float = 0.0
    user_fit_score: float = 0.0
    approach_fit_score: float = 0.0

@dataclass
class CLICandidate(Candidate):
    provider: str = "gemini"
    capabilities: CLICapabilityScores = field(default_factory=CLICapabilityScores)
    requires_api_key: bool = True

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
    selected_models: Dict[str, ModelCandidate] = field(default_factory=dict) # mapped by use_case
    selected_cli: Optional[CLICandidate] = None
    
    # Installation manifest (The final "To-Do" list)
    manifest: Dict[str, Any] = field(default_factory=dict)
    
    reasoning: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
