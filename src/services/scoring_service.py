import logging
from typing import List, Dict, Any, Optional
from dataclasses import replace

from src.schemas.recommendation import (
    ModelCandidate,
    CLICandidate,
    UserProfile,
    HardwareConstraints,
    RecommendationResult,
    ModelCapabilityScores,
    CLICapabilityScores
)
from src.schemas.environment import EnvironmentReport
from src.utils.logger import get_logger

log = get_logger(__name__)

class ScoringService:
    """
    Implements the Weighted Scoring Algorithm defined in Spec Section 13.5.
    Calculates fit scores for Models and CLI providers based on:
    1. Hardware Capabilities (50%)
    2. User Preferences (35%)
    3. Approach/Workflow Fit (15%)
    """

    def __init__(self, resources: Dict[str, Any]):
        """
        Args:
            resources: The full resources.json dictionary.
        """
        self.resources = resources
        self.config = resources.get("recommendation_config", {})
        self.weights = self.config.get("scoring_weights", {})
        self.hard_limits = self.config.get("hard_limits", {})

    def score_model_candidates(
        self,
        candidates: List[ModelCandidate],
        user_profile: UserProfile,
        hardware: HardwareConstraints
    ) -> List[ModelCandidate]:
        """
        Score and rank a list of model candidates.
        """
        scored_candidates = []
        
        for candidate in candidates:
            # 1. Check Hard Limits (Pass/Fail)
            if not self._check_hard_limits(candidate, hardware):
                candidate.composite_score = 0.0
                scored_candidates.append(candidate)
                continue

            # 2. Calculate Component Scores
            hw_score = self._calculate_hardware_fit(candidate, hardware)
            user_score = self._calculate_user_fit(candidate, user_profile)
            approach_score = self._calculate_approach_fit(candidate, user_profile)

            # 3. Calculate Composite Score
            # Weights: Hardware 50%, User 35%, Approach 15%
            comp_weights = self.weights.get("composite", {"hardware_fit": 0.5, "user_fit": 0.35, "approach_fit": 0.15})
            
            composite = (
                (hw_score * comp_weights.get("hardware_fit", 0.5)) +
                (user_score * comp_weights.get("user_fit", 0.35)) +
                (approach_score * comp_weights.get("approach_fit", 0.15))
            )

            # Update Candidate
            candidate.hardware_fit_score = hw_score
            candidate.user_fit_score = user_score
            candidate.approach_fit_score = approach_score
            candidate.composite_score = round(max(0.0, min(1.0, composite)), 3)
            
            scored_candidates.append(candidate)

        # Sort by composite score descending
        return sorted(scored_candidates, key=lambda x: x.composite_score, reverse=True)

    def _check_hard_limits(self, candidate: ModelCandidate, hardware: HardwareConstraints) -> bool:
        """
        Returns False if candidate violates hard hardware limits.
        Updates candidate.rejection_reason if rejected.
        """
        # Flux VRAM Limit
        if candidate.tier == "flux" and hardware.vram_gb < self.hard_limits.get("flux_min_vram", 12):
            candidate.rejection_reason = f"Insufficient VRAM for Flux (Needs {self.hard_limits.get('flux_min_vram')}GB, Has {hardware.vram_gb}GB)"
            return False
        
        # SDXL VRAM Limit
        if candidate.tier == "sdxl" and hardware.vram_gb < self.hard_limits.get("sdxl_min_vram", 8):
            candidate.rejection_reason = f"Insufficient VRAM for SDXL (Needs {self.hard_limits.get('sdxl_min_vram')}GB, Has {hardware.vram_gb}GB)"
            return False

        # Video Generation Limit
        if "i2v" in candidate.requirements.get("capabilities", []) and hardware.vram_gb < self.hard_limits.get("video_min_vram", 8):
            candidate.rejection_reason = f"Insufficient VRAM for Video Generation (Needs {self.hard_limits.get('video_min_vram')}GB)"
            return False

        return True

    def _calculate_hardware_fit(self, candidate: ModelCandidate, hardware: HardwareConstraints) -> float:
        """
        Calculates 0.0-1.0 score based on hardware suitability.
        """
        base_score = 1.0
        penalties = self.weights.get("hardware_penalties", {})
        bonuses = self.weights.get("hardware_bonuses", {})

        # Penalty: Quantization Required (if candidate is GGUF but hardware is powerful enough for full)
        # Note: This logic is tricky. Usually we penalize if we *have* to quantize on low hardware.
        # Here we follow the logic: If hardware specifically requires quantization (e.g. Apple Silicon or Low VRAM)
        # and the candidate IS quantized, that's a good fit (no penalty). 
        # If hardware is low end and candidate is NOT quantized, that's a bad fit (handled by hard limits or high vram usage).
        
        # Let's simplify: Start perfect, subtract for "frictions".
        
        # Friction: Running on Battery
        # We don't have battery state in HardwareConstraints yet, assuming False for now or added later.
        
        # Friction: Thermal Throttling Risk
        if hardware.expected_thermal_throttle:
             base_score += penalties.get("thermal_throttle_risk", -0.20)

        # Friction: Storage constraints
        if not hardware.storage_adequate:
             base_score += penalties.get("storage_over_50pct", -0.15)
        
        # Bonus: Good Thermal Headroom for Demanding Models
        if not hardware.expected_thermal_throttle and candidate.tier in ["flux", "sdxl"]:
            base_score += bonuses.get("good_thermal_demanding_model", 0.05)

        return max(0.0, min(1.0, base_score))

    def _calculate_user_fit(self, candidate: ModelCandidate, user_profile: UserProfile) -> float:
        """
        Calculates 0.0-1.0 score based on user preferences (ContentPreferences).
        """
        score = 0.5 # Neutral start
        
        # If no specific preferences, return neutral
        if not user_profile.content_preferences:
            return score

        # Iterate through preferences for the relevant use case
        # For simplicity, we'll aggregate scores from all defined preferences if multiple exist,
        # or just pick the first one. In reality, we should score against the specific use case being evaluated.
        # But ModelCandidate doesn't explicitly state which use case it solves without context.
        # We will assume the caller filters candidates by use case first.
        
        # Let's use the first available content preference for now
        if not user_profile.content_preferences:
            return 0.5
            
        prefs = list(user_profile.content_preferences.values())[0]
        
        # 1. Quality Match (Photorealism, Stylization)
        # Normalized difference: 1.0 - (abs(pref - cap) / 5.0)
        # This assumes preferences are 1-5 and capabilities are 0.0-1.0. 
        # We need to map 1-5 to 0.0-1.0 for comparison.
        
        def norm(val_1to5):
            return (val_1to5 - 1) / 4.0

        diff_photorealism = abs(norm(prefs.photorealism) - candidate.capabilities.photorealism)
        diff_stylization = abs(norm(prefs.artistic_stylization) - candidate.capabilities.artistic_stylization)
        
        # Closer match is better. 
        # If user wants High Photorealism (5->1.0) and Model is (0.9), diff is 0.1. Score should be high.
        # Score contribution: (1.0 - diff)
        
        score += (1.0 - diff_photorealism) * 0.1 # Weight 10%
        score += (1.0 - diff_stylization) * 0.1 # Weight 10%
        
        # 2. Speed Preference
        # If user prioritizes speed (5), and model is fast (0.9), good match.
        diff_speed = abs(norm(prefs.generation_speed) - candidate.capabilities.generation_speed)
        score += (1.0 - diff_speed) * 0.1

        # 3. Style Tags Bonus
        # If candidate has tags that match user style tags
        # Not currently in ModelCandidate schema, but would go here.
        
        return max(0.0, min(1.0, score))

    def _calculate_approach_fit(self, candidate: ModelCandidate, user_profile: UserProfile) -> float:
        """
        Calculates 0.0-1.0 score based on workflow complexity vs user experience.
        """
        score = 1.0
        penalties = self.weights.get("approach_penalties", {})
        
        # 1. Complexity Penalty for Beginners
        if user_profile.proficiency == "Beginner":
            # If candidate requires complex setup or many nodes
            if len(candidate.required_nodes) > 3:
                score += penalties.get("too_many_nodes_for_simplicity", -0.20)
                candidate.reasoning.append("Complex workflow may be difficult for beginners.")
                
            # If approach is "monolithic" (simple) vs "modular" (complex)
            if candidate.approach != "minimal" and user_profile.prefer_simple_setup >= 4:
                score += penalties.get("approach_mismatch", -0.40)
        
        # 2. Simplicity Penalty for Experts (They might want control)
        if user_profile.proficiency == "Expert":
            if candidate.approach == "minimal":
                score -= 0.1 # Slight penalty, experts prefer control
                candidate.reasoning.append("Minimal workflow may limit expert control.")

        return max(0.0, min(1.0, score))

    def score_cli_candidates(
        self,
        candidates: List[CLICandidate],
        user_profile: UserProfile
    ) -> List[CLICandidate]:
        """
        Score CLI providers.
        """
        scored = []
        for cand in candidates:
            score = 0.5
            
            # Use Case Match
            # If user wants coding, and CLI is good at coding
            if user_profile.cli_preferences:
                if "coding" in user_profile.cli_preferences.primary_tasks:
                     score += cand.capabilities.coding * 0.2
                if "writing" in user_profile.cli_preferences.primary_tasks:
                     score += cand.capabilities.creative_writing * 0.2
            
            # Local vs Cloud Preference
            if user_profile.prefer_local_processing >= 4:
                if cand.capabilities.local_execution > 0.8:
                    score += 0.3
                else:
                    score -= 0.3
                    cand.reasoning.append("Does not run locally.")
            
            cand.composite_score = max(0.0, min(1.0, score))
            scored.append(cand)
            
        return sorted(scored, key=lambda x: x.composite_score, reverse=True)
