from typing import List, Dict, Any, Optional
from src.schemas.environment import EnvironmentReport
from src.schemas.recommendation import (
    ModuleRecommendation,
    HardwareConstraints,
    ModelCandidate,
    ModelCapabilityScores,
    UserProfile,
    CLICandidate,
    CLICapabilityScores,
    CloudRankedCandidate,
    RecommendationResults,
)
from src.services.scoring_service import ScoringService
from src.services.model_database import (
    ModelDatabase,
    ModelEntry,
    ModelVariant,
    get_model_database,
    normalize_platform,
)
from src.services.recommendation.cloud_layer import CloudRecommendationLayer
from src.utils.logger import log


# Storage threshold for warnings (per PLAN: Cloud API Integration)
STORAGE_WARNING_THRESHOLD_GB = 50


class RecommendationService:
    """
    Generates configuration recommendations for modules based on
    User Profile and Hardware Environment.

    CORE DATA SOURCES (Source of Truth):
    - Models: models_database.yaml via ModelDatabase (Phase 1-3 target: models.db)
    - System Tools & Use Cases: resources.json (v2.0+)
    - Preferences: UserProfile schema

    LEGACY NOTE:
    This service is in transition from ScoringService (weighted) to the
    3-layer TOPSIS recommendation engine (RecommendationOrchestrator).
    """

    def __init__(self, resources: Dict[str, Any], model_db: Optional[ModelDatabase] = None):
        """
        Initialize the recommendation service.

        Args:
            resources: Config from resources.json (use_cases, modules, etc.)
            model_db: Optional ModelDatabase instance. If None, uses singleton.
        """
        self.resources = resources
        self.model_db = model_db or get_model_database()
        
        # LEGACY: To be removed once _run_local_pipeline is refactored
        self.scoring_service = ScoringService(resources)
        
                # MODERN: Orchestration Facade (Task PAT-01)
                from src.services.recommendation.orchestrator import RecommendationOrchestrator
                from src.services.recommendation.manifest_orchestrator import ManifestOrchestrator
                
                self.orchestrator = RecommendationOrchestrator(model_db=self.model_db)
                self.manifest_orchestrator = ManifestOrchestrator(model_db=self.model_db)
                
                self.cloud_layer = CloudRecommendationLayer(model_db=self.model_db)
            def generate_recommendations(
        self,
        use_case: str,
        env: EnvironmentReport,
        user_profile: UserProfile
    ) -> List[ModuleRecommendation]:
        """
        Generate recommendations for all modules relevant to use case.

        NOTE: This is the LEGACY module-based recommendation method.
        For the new parallel local/cloud pathway system, use generate_parallel_recommendations().
        """
        recommendations = []
        use_case_config = self.resources.get("use_cases", {}).get(use_case)

        log.info(f"generate_recommendations: use_case={use_case}, "
                 f"available_use_cases={list(self.resources.get('use_cases', {}).keys())}")

        if not use_case_config:
            log.error(f"Unknown use case: {use_case}")
            return []

        log.info(f"use_case_config: modules={use_case_config.get('modules', [])}, "
                 f"optional_modules={use_case_config.get('optional_modules', [])}")

        # Convert EnvironmentReport to HardwareConstraints (Normalized)
        hardware_constraints = self._normalize_hardware(env)

        # 1. ComfyUI Recommendation
        if "comfyui" in use_case_config.get("modules", []):
            log.info("Generating ComfyUI recommendation...")
            comfy_rec = self._recommend_comfyui(use_case_config, env, hardware_constraints, user_profile)
            recommendations.append(comfy_rec)
            log.info(f"ComfyUI recommendation: enabled={comfy_rec.enabled}")

        # 2. CLI Provider Recommendation
        if "cli_provider" in use_case_config.get("modules", []) or "cli_provider" in use_case_config.get("optional_modules", []):
            log.info("Generating CLI provider recommendation...")
            cli_rec = self._recommend_cli_provider(use_case_config, env, hardware_constraints, user_profile)
            recommendations.append(cli_rec)
            log.info(f"CLI provider recommendation: provider={cli_rec.config.get('provider')}")

        log.info(f"generate_recommendations complete: {len(recommendations)} modules for use_case={use_case}")
        return recommendations

    def generate_parallel_recommendations(
        self,
        user_profile: UserProfile,
        env: EnvironmentReport,
        categories: Optional[List[str]] = None,
    ) -> RecommendationResults:
        """
        Generate recommendations using parallel pathways.

        Per PLAN: Cloud API Integration - Runs local and/or cloud pathways
        based on user's cloud_willingness setting.

        Args:
            user_profile: User's preferences including cloud_api_preferences
            env: Environment report with hardware info
            categories: Optional list of categories to filter

        Returns:
            RecommendationResults with local and/or cloud recommendations
        """
        results = RecommendationResults()
        willingness = user_profile.cloud_api_preferences.cloud_willingness

        # Normalize hardware for local pathway
        hardware = self._normalize_hardware(env)

        # Track storage constraint
        storage_free_gb = env.disk_free_gb
        results.storage_constrained = storage_free_gb < STORAGE_WARNING_THRESHOLD_GB

        # Run local pathway (unless cloud_only)
        if willingness != "cloud_only":
            results.local_recommendations = self._run_local_pipeline(
                user_profile, hardware, env, categories
            )

            # Add storage warnings for large local models
            if results.storage_constrained:
                results.storage_warnings = self._generate_storage_warnings(
                    results.local_recommendations, storage_free_gb
                )

        # Run cloud pathway (unless local_only)
        if willingness != "local_only":
            results.cloud_recommendations = self.cloud_layer.recommend(
                user_profile=user_profile,
                categories=categories,
                storage_free_gb=storage_free_gb,
            )

        # Determine primary pathway
        results.primary_pathway = (
            "cloud" if willingness in ["cloud_preferred", "cloud_only"]
            else "local"
        )

        log.info(
            f"Generated parallel recommendations: "
            f"{len(results.local_recommendations)} local, "
            f"{len(results.cloud_recommendations)} cloud, "
            f"primary={results.primary_pathway}"
        )

        return results

    def generate_full_manifest(
        self,
        user_profile: UserProfile,
        recommendations: List[RankedCandidate]
    ) -> InstallationManifest:
        """
        Takes chosen recommendations and builds a full installation plan.
        """
        log.info(f"Building full manifest for {len(recommendations)} chosen models...")
        return self.manifest_orchestrator.create_manifest(recommendations, user_profile)

    def _run_local_pipeline(
        self,
        user_profile: UserProfile,
        hardware: HardwareConstraints,
        env: EnvironmentReport,
        categories: Optional[List[str]] = None,
    ) -> List[ModelCandidate]:
        """
        Run the local model recommendation pipeline.

        Args:
            user_profile: User's preferences
            hardware: Normalized hardware constraints
            env: Environment report
            categories: Optional category filter

        Returns:
            List of ModelCandidate sorted by score
        """
        # 1. Prepare modern HardwareProfile from EnvironmentReport
        # (This transformation logic will eventually move to PAT-04 Adapter)
        from src.services.hardware import detect_hardware
        try:
            full_hardware = detect_hardware()
        except Exception:
            # Fallback to normalized constraints if full detection fails during transition
            from src.schemas.hardware import HardwareProfile, PlatformType
            full_hardware = HardwareProfile(
                gpu_vendor=env.gpu_vendor,
                gpu_name=env.gpu_name,
                vram_gb=env.vram_gb,
                platform=env.os_name # Simplified
            )

        # 2. Execute modern 3-layer orchestration
        # We use 'full_stack' as a default use_case key for the internal logic
        ranked, rejected = self.orchestrator.recommend_models(
            hardware=full_hardware,
            user_profile=user_profile,
            use_case="full_stack",
            categories=categories
        )

        if not ranked:
            return []

        # 3. Transform RankedCandidate -> Legacy ModelCandidate (Compatibility Layer)
        legacy_candidates = []
        for r in ranked:
            scored_cand = r.scored_candidate
            passing_cand = scored_cand.passing_candidate
            
            # Map modern scores to legacy composite_score
            legacy_cand = self._model_to_candidate(
                passing_cand.model, 
                passing_cand.variant, 
                full_hardware.platform
            )
            legacy_cand.composite_score = r.closeness_coefficient
            legacy_cand.reasoning = [r.explanation]
            
            legacy_candidates.append(legacy_cand)

        return legacy_candidates

    def _generate_storage_warnings(
        self,
        candidates: List[ModelCandidate],
        storage_free_gb: float,
    ) -> List[str]:
        """
        Generate storage warnings for large local models.

        Per PLAN: Cloud API Integration - Warn users about storage impact.

        Args:
            candidates: Local model candidates
            storage_free_gb: Free storage space in GB

        Returns:
            List of warning strings
        """
        warnings = []

        for candidate in candidates[:5]:  # Top 5 candidates
            size_gb = candidate.requirements.get("size_gb", 0)
            if size_gb > 0:
                usage_percent = (size_gb / storage_free_gb) * 100
                if usage_percent > 50:
                    warnings.append(
                        f"{candidate.display_name} ({size_gb:.1f}GB) would use "
                        f"{usage_percent:.0f}% of your free space"
                    )

        return warnings

    def _recommend_comfyui(
        self,
        use_case_config: Dict,
        env: EnvironmentReport,
        hardware: HardwareConstraints,
        user_profile: UserProfile
    ) -> ModuleRecommendation:

        # Determine categories based on use case capabilities
        capabilities = use_case_config.get("capabilities", [])
        categories = self._capabilities_to_categories(capabilities)

        # 1. Generate Candidates from ModelDatabase (replaces resources.json)
        candidates = self._generate_model_candidates(env, categories)
        
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
        from src.config.constants import VENV_SIZE_ESTIMATE_GB
        est_size = best_candidate.requirements.get("size_gb", 2.0) + VENV_SIZE_ESTIMATE_GB
        
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
        
        # Simple selection for now.
        # TODO: Migrate to RecommendationOrchestrator (3-layer)
        
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

    def _generate_model_candidates(
        self,
        env: EnvironmentReport,
        categories: Optional[List[str]] = None,
    ) -> List[ModelCandidate]:
        """
        Generate model candidates from ModelDatabase.

        This replaces the legacy resources.json model loading.

        Args:
            env: Environment report with hardware info
            categories: Optional list of categories to filter (None = all local models)

        Returns:
            List of ModelCandidate objects for scoring
        """
        candidates = []

        # Determine platform key from environment
        platform = normalize_platform(env.gpu_vendor, env.os_name)

        # Get VRAM in MB (convert from GB)
        vram_mb = int(env.vram_gb * 1024)

        # Get compute capability if available
        compute_cap = None
        if hasattr(env, "cuda_compute_capability") and env.cuda_compute_capability:
            compute_cap = env.cuda_compute_capability

        # Default categories if not specified
        if categories is None:
            categories = ["image_generation", "video_generation"]

        # Get compatible models from database
        compatible = self.model_db.get_compatible_models(
            platform=platform,
            vram_mb=vram_mb,
            categories=categories,
            compute_capability=compute_cap,
        )

        for model, variant in compatible:
            candidate = self._model_to_candidate(model, variant, platform)
            candidates.append(candidate)

        log.info(f"Generated {len(candidates)} model candidates for {platform} with {vram_mb}MB VRAM")
        return candidates

    def _model_to_candidate(
        self,
        model: ModelEntry,
        variant: ModelVariant,
        platform: str,
    ) -> ModelCandidate:
        """
        Convert a ModelEntry + ModelVariant to a ModelCandidate.

        Args:
            model: The model entry from database
            variant: The selected variant
            platform: Platform key for node filtering

        Returns:
            ModelCandidate ready for scoring
        """
        # Map capability scores from YAML schema to ModelCapabilityScores
        cap_scores = ModelCapabilityScores()
        yaml_scores = model.capabilities.scores

        # Map common score names
        score_mapping = {
            "photorealism": "photorealism",
            "artistic_quality": "artistic_stylization",
            "speed": "generation_speed",
            "temporal_coherence": "temporal_coherence",
            "motion_quality": "motion_dynamic",
            "consistency": "output_fidelity",
            "text_rendering": "prompt_adherence",
        }

        for yaml_key, attr_name in score_mapping.items():
            if yaml_key in yaml_scores and hasattr(cap_scores, attr_name):
                setattr(cap_scores, attr_name, yaml_scores[yaml_key])

        # Determine tier from model family/architecture
        tier = self._determine_tier(model, variant)

        # Get required nodes
        required_nodes = self.model_db.get_required_nodes(model, variant)

        # Build requirements dict
        requirements = {
            "url": variant.download_url,
            "size_gb": variant.download_size_gb,
            "vram_min_mb": variant.vram_min_mb,
            "vram_recommended_mb": variant.vram_recommended_mb,
            "precision": variant.precision,
            "quality_retention": variant.quality_retention_percent,
        }

        # Determine approach based on model complexity
        approach = self._determine_approach(model)

        return ModelCandidate(
            id=f"{model.id}_{variant.id}",
            display_name=f"{model.name} ({variant.precision.upper()})",
            tier=tier,
            category=model.category,  # Pass category for modality filtering
            capabilities=cap_scores,
            requirements=requirements,
            approach=approach,
            required_nodes=required_nodes,
        )

    def _determine_tier(self, model: ModelEntry, variant: ModelVariant) -> str:
        """
        Determine tier classification from model data.

        Maps to legacy tier names for compatibility with scoring_service.
        """
        family = model.family.lower()
        vram_min = variant.vram_min_mb

        # Map by VRAM requirements (legacy tier system)
        if vram_min >= 24000:
            return "flux"
        elif vram_min >= 12000:
            return "flux"
        elif vram_min >= 8000:
            return "sdxl"
        elif "gguf" in variant.precision.lower():
            return "gguf"
        else:
            return "sd15"

    def _determine_approach(self, model: ModelEntry) -> str:
        """
        Determine recommended approach from model characteristics.

        Returns:
            "minimal", "monolithic", or "modular"
        """
        # Check for complex dependencies
        if model.dependencies.paired_models:
            return "modular"

        # Check for multiple required nodes
        if len(model.dependencies.required_nodes) > 2:
            return "modular"

        # Default to minimal for simpler setups
        return "minimal"

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

    def _capabilities_to_categories(self, capabilities: List[str]) -> List[str]:
        """
        Map use case capabilities to model database categories.

        Args:
            capabilities: List of capability strings from use_case config
                         e.g., ["t2i", "i2i", "i2v"]

        Returns:
            List of category strings for ModelDatabase query
                         e.g., ["image_generation", "video_generation"]
        """
        # Mapping from capability codes to database categories
        capability_map = {
            # Image capabilities
            "t2i": "image_generation",
            "i2i": "image_generation",
            "text_to_image": "image_generation",
            "image_to_image": "image_generation",
            "inpainting": "image_generation",
            "outpainting": "image_generation",

            # Video capabilities
            "i2v": "video_generation",
            "t2v": "video_generation",
            "image_to_video": "video_generation",
            "text_to_video": "video_generation",
            "video_editing": "video_generation",

            # Audio capabilities
            "tts": "audio_generation",
            "text_to_speech": "audio_generation",
            "voice_cloning": "audio_generation",
            "music": "audio_generation",
            "music_generation": "audio_generation",

            # 3D capabilities
            "i2_3d": "3d_generation",
            "t2_3d": "3d_generation",
            "image_to_3d": "3d_generation",
            "text_to_3d": "3d_generation",

            # Lip sync
            "lip_sync": "lip_sync",
            "talking_head": "lip_sync",
        }

        categories = set()

        for cap in capabilities:
            cap_lower = cap.lower()
            if cap_lower in capability_map:
                categories.add(capability_map[cap_lower])

        # Default to image_generation if no capabilities specified
        if not categories:
            categories.add("image_generation")

        return list(categories)