"""
Resolution Cascade for handling constraint failures.
Part of Task PAT-02: Template Method for Resolution Cascade.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Set

from src.schemas.hardware import HardwareProfile, PlatformType
from src.schemas.model import ModelEntry, ModelVariant
from src.schemas.recommendation import RejectionReason
from src.config.constants import DEFAULT_QUANT_PRIORITY, MPS_SAFE_QUANTS


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
SUBSTITUTION_MAP: Dict[str, List[Tuple[str, float]]] = {
    "flux": [("flux_schnell", 0.85), ("sdxl", 0.75)],
    "flux_dev": [("flux_schnell", 0.90), ("sdxl", 0.75)],
    "sdxl": [("sd15", 0.65)],
    "hunyuan_video": [("wan21", 0.80), ("animatediff", 0.60)],
    "wan21": [("animatediff", 0.75)],
    "cogvideox": [("wan21", 0.85), ("animatediff", 0.65)],
    "sd15": [],
    "animatediff": [],
}

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

WORKFLOW_ADJUSTMENTS: Dict[str, Dict[str, str]] = {
    "reduce_resolution": {
        "description": "Generate at lower resolution, then upscale",
        "from": "1024x1024", "to": "768x768 or 512x512",
        "impact": "Faster generation, may lose fine details",
    },
    "reduce_batch": {
        "description": "Generate fewer images per batch",
        "from": "4+ images", "to": "1-2 images",
        "impact": "Lower VRAM usage, slower throughput",
    },
    "reduce_steps": {
        "description": "Use fewer inference steps",
        "from": "30+ steps", "to": "15-20 steps",
        "impact": "Faster generation, may affect quality",
    },
    "video_shorter": {
        "description": "Generate shorter video clips",
        "from": "4+ seconds", "to": "2 seconds",
        "impact": "Lower VRAM usage, more clips needed",
    },
}


class BaseResolutionCascade(ABC):
    """
    ABSTRACT BASE CLASS (Template Method Pattern).
    Defines the skeleton of the resolution fallback algorithm.
    """
    
    def __init__(self, model_database: Dict[str, ModelEntry]):
        self.model_db = model_database

    def resolve(
        self,
        model: ModelEntry,
        hardware: HardwareProfile,
        failure_reason: str,
        use_case: str,
    ) -> ResolutionResult:
        """
        The Template Method. Defines the fixed sequence of resolution attempts.
        """
        result = ResolutionResult(original_model_id=model.id, resolved=False)

        # 1. Step: Quantization
        attempt = self.try_quantization(model, hardware)
        result.attempts.append(attempt)
        if attempt.success:
            return self._finalize_result(result, ResolutionStrategy.QUANTIZATION, model, attempt)

        # 2. Step: CPU Offload
        attempt = self.try_cpu_offload(model, hardware)
        result.attempts.append(attempt)
        if attempt.success:
            return self._finalize_result(result, ResolutionStrategy.CPU_OFFLOAD, model, attempt)

        # 3. Step: Substitution
        attempt = self.try_substitution(model, hardware, use_case)
        result.attempts.append(attempt)
        if attempt.success:
            return self._finalize_result(result, ResolutionStrategy.SUBSTITUTION, model, attempt)

        # 4. Step: Workflow Adjustment
        attempt = self.try_workflow_adjustment(model, hardware, use_case)
        result.attempts.append(attempt)
        if attempt.success:
            return self._finalize_result(result, ResolutionStrategy.WORKFLOW_ADJUSTMENT, model, attempt)

        # 5. Step: Cloud Fallback
        attempt = self.try_cloud_fallback(model, use_case)
        result.attempts.append(attempt)
        if attempt.success:
            return self._finalize_result(result, ResolutionStrategy.CLOUD_FALLBACK, model, attempt)

        # Failure Message
        result.user_message = f"Unable to run {model.name} on your hardware. No alternatives found."
        return result

    @abstractmethod
    def try_quantization(self, model: ModelEntry, hardware: HardwareProfile) -> ResolutionAttempt: pass

    @abstractmethod
    def try_cpu_offload(self, model: ModelEntry, hardware: HardwareProfile) -> ResolutionAttempt: pass

    @abstractmethod
    def try_substitution(self, model: ModelEntry, hardware: HardwareProfile, use_case: str) -> ResolutionAttempt: pass

    @abstractmethod
    def try_workflow_adjustment(self, model: ModelEntry, hardware: HardwareProfile, use_case: str) -> ResolutionAttempt: pass

    @abstractmethod
    def try_cloud_fallback(self, model: ModelEntry, use_case: str) -> ResolutionAttempt: pass

    def _finalize_result(self, result: ResolutionResult, strategy: ResolutionStrategy, model: ModelEntry, attempt: ResolutionAttempt) -> ResolutionResult:
        """Helper to fill common result fields upon success."""
        result.resolved = True
        result.final_strategy = strategy
        result.user_message = attempt.details
        if attempt.performance_impact:
            result.warnings.append(attempt.performance_impact)
        return result


class StandardResolutionCascade(BaseResolutionCascade):
    """
    Standard implementation of the resolution fallback steps.
    """
    QUANT_PRIORITY = DEFAULT_QUANT_PRIORITY
    MPS_SAFE_QUANTS = MPS_SAFE_QUANTS

    def try_quantization(self, model: ModelEntry, hardware: HardwareProfile) -> ResolutionAttempt:
        vram_mb = int(hardware.vram_gb * 1024)
        is_apple = hardware.platform == PlatformType.APPLE_SILICON
        
        available = []
        for var in model.variants:
            if is_apple and var.precision.lower() not in self.MPS_SAFE_QUANTS: continue
            if var.vram_min_mb <= vram_mb: available.append(var)

        if not available: return ResolutionAttempt(ResolutionStrategy.QUANTIZATION, False, details="No fits")

        # Pick best by priority
        for q in self.QUANT_PRIORITY:
            for var in available:
                if var.precision.lower() == q:
                    return ResolutionAttempt(ResolutionStrategy.QUANTIZATION, True, result=q, details=f"Using {q}")
        
        return ResolutionAttempt(ResolutionStrategy.QUANTIZATION, True, result=available[0].precision, details="Found fit")

    def try_cpu_offload(self, model: ModelEntry, hardware: HardwareProfile) -> ResolutionAttempt:
        if not hardware.ram: return ResolutionAttempt(ResolutionStrategy.CPU_OFFLOAD, False)
        
        effective_mb = int(hardware.vram_gb * 1024) + int(hardware.ram.usable_for_offload_gb * 1024)
        for var in model.variants:
            if var.vram_min_mb <= effective_mb:
                return ResolutionAttempt(ResolutionStrategy.CPU_OFFLOAD, True, result=var.precision, details="Offload viable", performance_impact="5-10x slower")
        
        return ResolutionAttempt(ResolutionStrategy.CPU_OFFLOAD, False)

    def try_substitution(self, model: ModelEntry, hardware: HardwareProfile, use_case: str) -> ResolutionAttempt:
        family = model.family.lower()
        substitutes = SUBSTITUTION_MAP.get(family, [])
        if not substitutes:
            return ResolutionAttempt(ResolutionStrategy.SUBSTITUTION, False, details=f"No substitutes for {family}")
        
        vram_mb = int(hardware.vram_gb * 1024)
        is_apple = hardware.platform == PlatformType.APPLE_SILICON
        
        for sub_family, ratio in substitutes:
            for mid, cand in self.model_db.items():
                if cand.family.lower() == sub_family:
                    # Check if substitute fits
                    fit = False
                    for var in cand.variants:
                        if is_apple and var.precision.lower() not in self.MPS_SAFE_QUANTS: continue
                        if var.vram_min_mb <= vram_mb:
                            fit = True
                            break
                    if fit:
                        return ResolutionAttempt(ResolutionStrategy.SUBSTITUTION, True, result=mid, details=f"Suggest {cand.name} instead")
                    
        return ResolutionAttempt(ResolutionStrategy.SUBSTITUTION, False, details="No fitting substitutes found")

    def try_workflow_adjustment(self, model: ModelEntry, hardware: HardwareProfile, use_case: str) -> ResolutionAttempt:
        vram_mb = int(hardware.vram_gb * 1024)
        min_vram = min([v.vram_min_mb for v in model.variants], default=0)
        gap = min_vram - vram_mb
        
        if gap <= 0:
            return ResolutionAttempt(ResolutionStrategy.WORKFLOW_ADJUSTMENT, False, details="Fits natively")
            
        if gap > 4096:
            return ResolutionAttempt(ResolutionStrategy.WORKFLOW_ADJUSTMENT, False, details="VRAM gap too large")

        msg = "Try lower resolution (768x768)"
        if "video" in use_case.lower():
            msg = "Try shorter video clips"
            
        return ResolutionAttempt(ResolutionStrategy.WORKFLOW_ADJUSTMENT, True, details=msg)

    def try_cloud_fallback(self, model: ModelEntry, use_case: str) -> ResolutionAttempt:
        opts = []
        if hasattr(model, "cloud") and model.cloud:
            if model.cloud.partner_node: opts.append("Partner Node")
            if model.cloud.replicate: opts.append("Replicate")
            
        details = "Cloud API recommended"
        if opts:
            details = f"Cloud options available: {', '.join(opts)}"
            
        return ResolutionAttempt(ResolutionStrategy.CLOUD_FALLBACK, True, result="cloud", details=details)


# Legacy compatibility
ResolutionCascade = StandardResolutionCascade

def create_cascade_for_hardware(hardware: HardwareProfile, model_database: Dict[str, ModelEntry]) -> ResolutionCascade:
    return ResolutionCascade(model_database)