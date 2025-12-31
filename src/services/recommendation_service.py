from typing import List, Dict, Any, Optional
from src.schemas.environment import EnvironmentReport
from src.schemas.recommendation import (
    ModuleRecommendation,
    HardwareConstraints,
    ModelCandidate,
    ModelCapabilityScores,
    UserProfile,
    CLICandidate,
    CLICapabilityScores
)
from src.services.scoring_service import ScoringService
from src.utils.logger import log

class RecommendationService:
    """
    Generates configuration recommendations for modules based on
    User Profile and Hardware Environment.
    """
    
    def __init__(self, resources: Dict[str, Any]):
        self.resources = resources
        self.scoring_service = ScoringService(resources)

    def generate_recommendations(
        self, 
        use_case: str, 
        env: EnvironmentReport,
        user_profile: UserProfile
    ) -> List[ModuleRecommendation]:
        """
        Generate recommendations for all modules relevant to use case.
        """
        recommendations = []
        use_case_config = self.resources.get("use_cases", {}).get(use_case)
        
        if not use_case_config:
            log.error(f"Unknown use case: {use_case}")
            return []

        # Convert EnvironmentReport to HardwareConstraints (Normalized)
        hardware_constraints = self._normalize_hardware(env)
        
        # 1. ComfyUI Recommendation
        if "comfyui" in use_case_config.get("modules", []):
            comfy_rec = self._recommend_comfyui(use_case_config, env, hardware_constraints, user_profile)
            recommendations.append(comfy_rec)
            
        # 2. CLI Provider Recommendation
        if "cli_provider" in use_case_config.get("modules", []) or "cli_provider" in use_case_config.get("optional_modules", []):
            cli_rec = self._recommend_cli_provider(use_case_config, env, hardware_constraints, user_profile)
            recommendations.append(cli_rec)
            
        return recommendations

    def _recommend_comfyui(
        self, 
        use_case_config: Dict, 
        env: EnvironmentReport,
        hardware: HardwareConstraints,
        user_profile: UserProfile
    ) -> ModuleRecommendation:
        
        # 1. Generate Candidates from Resources
        candidates = self._generate_model_candidates()
        
        # 2. Score Candidates
        scored_candidates = self.scoring_service.score_model_candidates(candidates, user_profile, hardware)
        
        if not scored_candidates:
            return ModuleRecommendation(
                module_id="comfyui",
                enabled=False,
                display_name="ComfyUI Studio",
                description="Visual AI generation studio.",
                config={},
                reasoning=["No compatible models found for your hardware."],
                warnings=["Your hardware does not meet the minimum requirements."],
                components=[],
                estimated_size_gb=0,
                estimated_time_minutes=0
            )

        # 3. Select Best Candidate
        # Filter out rejected
        valid_candidates = [c for c in scored_candidates if c.composite_score > 0]
        
        if not valid_candidates:
             # All rejected
             best = scored_candidates[0] # The least bad one? Or just fail.
             # Return disabled recommendation with reason
             return ModuleRecommendation(
                module_id="comfyui",
                enabled=False,
                display_name="ComfyUI Studio",
                description="Visual AI generation studio.",
                config={},
                reasoning=[f"Best option {best.display_name} rejected: {best.rejection_reason}"],
                warnings=["Hardware insufficient."],
                components=[],
                estimated_size_gb=0,
                estimated_time_minutes=0
            )
             
        best_candidate = valid_candidates[0]
        
        # 4. Construct Configuration
        # This mirrors the logic needed to build the manifest later
        required_nodes = ["ComfyUI-Manager"] + best_candidate.required_nodes
        
        # Add use-case specific nodes
        uc_conf = use_case_config.get("comfyui_config", {})
        if "required_nodes" in uc_conf:
            required_nodes.extend(uc_conf["required_nodes"])
            
        config = {
            "model_tier": best_candidate.tier,
            "selected_model": best_candidate.display_name,
            "selected_model_url": best_candidate.requirements.get("url"), # Simplify for now
            "required_nodes": list(set(required_nodes))
        }

        # Estimate Size
        est_size = best_candidate.requirements.get("size_gb", 2.0) + 1.5 # Core + Venv approx
        
        return ModuleRecommendation(
            module_id="comfyui",
            enabled=True,
            display_name="ComfyUI Studio",
            description="Visual AI generation studio.",
            config=config,
            reasoning=best_candidate.reasoning + [f"Selected {best_candidate.display_name} (Score: {best_candidate.composite_score})"],
            warnings=[],
            components=["Core", "Manager"] + required_nodes + [best_candidate.display_name],
            estimated_size_gb=est_size,
            estimated_time_minutes=int(est_size * 5) # Rough 5 min/GB on avg connection
        )

    def _recommend_cli_provider(
        self,
        use_case_config: Dict,
        env: EnvironmentReport,
        hardware: HardwareConstraints,
        user_profile: UserProfile
    ) -> ModuleRecommendation:
        
        # Simple selection for now, expandable later with ScoringService.score_cli_candidates
        # Default to Gemini for now as per project preference/availability
        
        return ModuleRecommendation(
            module_id="cli_provider",
            enabled=True,
            display_name="AI Assistant CLI",
            description="Command-line AI assistant.",
            config={"provider": "gemini"},
            reasoning=["Gemini provides a balanced mix of speed and capability."],
            warnings=[],
            components=["@google/gemini-cli"],
            estimated_size_gb=0.1,
            estimated_time_minutes=1
        )

    def _generate_model_candidates(self) -> List[ModelCandidate]:
        candidates = []
        models_res = self.resources.get("comfyui_components", {}).get("models", {})
        
        # Process Checkpoints
        checkpoints = models_res.get("checkpoints", {})
        for key, data in checkpoints.items():
            caps = data.get("capabilities", {})
            # Map dict caps to ModelCapabilityScores if detail available, 
            # currently resources.json has list ["t2i"] or dict. 
            # The schema in resources.json (read earlier) showed "capabilities": { "t2i": 1.0 ... }
            
            cap_scores = ModelCapabilityScores()
            if isinstance(caps, dict):
                # Update with values from json
                for k, v in caps.items():
                    if hasattr(cap_scores, k):
                        setattr(cap_scores, k, float(v))
            
            cand = ModelCandidate(
                id=key,
                display_name=data.get("display_name", key),
                tier=data.get("tier", "sd15"),
                capabilities=cap_scores,
                requirements={
                    "url": data.get("url"),
                    "size_gb": data.get("size_gb", 0),
                    "hash": data.get("hash")
                },
                approach="minimal" # Default
            )
            candidates.append(cand)
            
        # Process GGUF/UNETs
        unets = models_res.get("unet_gguf", {})
        for key, data in unets.items():
             # Similar logic
             cand = ModelCandidate(
                id=key,
                display_name=data.get("display_name", key),
                tier=data.get("tier", "gguf"),
                requirements={
                    "url": data.get("url"),
                    "size_gb": data.get("size_gb", 0)
                },
                required_nodes=["ComfyUI-GGUF"]
             )
             candidates.append(cand)
             
        return candidates

    def _normalize_hardware(self, env: EnvironmentReport) -> HardwareConstraints:
        """
        Normalize environment report into 0.0-1.0 scores.
        """
        constraints = HardwareConstraints()
        
        # Copy Raw
        constraints.gpu_vendor = env.gpu_vendor
        constraints.gpu_name = env.gpu_name
        constraints.vram_gb = env.vram_gb
        constraints.ram_gb = env.ram_gb
        constraints.disk_free_gb = env.disk_free_gb
        
        # Normalize VRAM (Reference: 24GB = 1.0)
        constraints.vram_score = min(1.0, env.vram_gb / 24.0)
        
        # Normalize RAM (Reference: 64GB = 1.0)
        constraints.ram_score = min(1.0, env.ram_gb / 64.0)
        
        # Normalize Storage (Reference: 500GB Free = 1.0)
        constraints.storage_score = min(1.0, env.disk_free_gb / 500.0)
        
        # Boolean constraints
        constraints.can_run_flux = env.vram_gb >= 12 or (env.gpu_vendor == "apple" and env.ram_gb >= 32)
        constraints.can_run_sdxl = env.vram_gb >= 8 or (env.gpu_vendor == "apple" and env.ram_gb >= 16)
        constraints.can_run_video = env.vram_gb >= 8 or (env.gpu_vendor == "apple" and env.ram_gb >= 16)
        
        # Storage check
        constraints.storage_adequate = env.disk_free_gb > 20 # Absolute minimum
        
        # Form Factor / Thermal hints
        constraints.expected_thermal_throttle = (env.form_factor == "laptop")
        
        return constraints