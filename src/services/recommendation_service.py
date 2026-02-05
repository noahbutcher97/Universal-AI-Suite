from typing import List, Dict, Any, Optional
from src.schemas.environment import EnvironmentReport
from src.schemas.model import ModelEntry, ModelVariant
from src.schemas.recommendation import (
    ModuleRecommendation,
    UserProfile,
    CLICandidate,
    CLICapabilityScores,
    CloudRankedCandidate,
    RecommendationResults,
    RankedCandidate
)
from src.schemas.installation import InstallationManifest
from src.services.model_database import (
    ModelDatabase,
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
        Now uses the modern 3-layer engine internally.
        """
        recommendations = []
        use_case_config = self.resources.get("use_cases", {}).get(use_case)

        if not use_case_config:
            log.error(f"Unknown use case: {use_case}")
            return []

        # 1. ComfyUI Recommendation (via model selection)
        if "comfyui" in use_case_config.get("modules", []):
            # For the legacy ModuleRecommendation return type, we pick the top model
            results = self.generate_parallel_recommendations(user_profile, env, None)
            if results.local_recommendations:
                best = results.local_recommendations[0]
                recommendations.append(ModuleRecommendation(
                    module_id="comfyui",
                    enabled=True,
                    display_name="ComfyUI Studio",
                    description="Visual AI generation studio.",
                    config={
                        "selected_model": best.display_name,
                        "required_nodes": best.required_nodes
                    },
                    reasoning=best.reasoning,
                    warnings=[],
                    components=["Core"] + best.required_nodes,
                    estimated_size_gb=best.requirements.get("size_gb", 2.0) + 1.5,
                    estimated_time_minutes=10
                ))

        # 2. CLI Provider Recommendation
        if "cli_provider" in use_case_config.get("modules", []) or "cli_provider" in use_case_config.get("optional_modules", []):
            cli_rec = self._recommend_cli_provider(use_case_config, env, None, user_profile)
            recommendations.append(cli_rec)

        return recommendations

    def generate_parallel_recommendations(
        self,
        user_profile: UserProfile,
        env: EnvironmentReport,
        categories: Optional[List[str]] = None,
        skip_snapshot: bool = False
    ) -> RecommendationResults:
        """
        Generate recommendations using parallel pathways.

        Per PLAN: Cloud API Integration - Runs local and/or cloud pathways
        based on user's cloud_willingness setting.

        Args:
            user_profile: User's preferences including cloud_api_preferences
            env: Environment report with hardware info
            categories: Optional list of categories to filter
            skip_snapshot: If True, skips hardware snapshot capture (Task DB-02)

        Returns:
            RecommendationResults with local and/or cloud recommendations
        """
        results = RecommendationResults()
        willingness = user_profile.cloud_api_preferences.cloud_willingness

        # Track storage constraint
        storage_free_gb = env.disk_free_gb
        results.storage_constrained = storage_free_gb < STORAGE_WARNING_THRESHOLD_GB

        # Run local pathway (unless cloud_only)
        if willingness != "cloud_only":
            results.local_recommendations = self._run_local_pipeline(
                user_profile, env, categories, skip_snapshot=skip_snapshot
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
        env: EnvironmentReport,
        categories: Optional[List[str]] = None,
        skip_snapshot: bool = False
    ) -> List[RankedCandidate]:
        """
        Run the local model recommendation pipeline.

        Args:
            user_profile: User's preferences
            env: Environment report
            categories: Optional category filter
            skip_snapshot: If True, skips hardware snapshot capture

        Returns:
            List of RankedCandidate sorted by score
        """
        # 1. Transform EnvironmentReport -> modern HardwareProfile
        from src.services.recommendation.hardware_adapter import HardwareAdapter
        full_hardware = HardwareAdapter.to_profile(env)

        # 2. Execute modern 3-layer orchestration
        # Use user's first primary use case if available, else default to full_stack
        use_case = "full_stack"
        if user_profile.primary_use_cases:
            use_case = user_profile.primary_use_cases[0]

        ranked, rejected = self.orchestrator.recommend_models(
            hardware=full_hardware,
            user_profile=user_profile,
            use_case=use_case,
            categories=categories,
            skip_snapshot=skip_snapshot
        )

        if not ranked:
            return []

        return ranked

    def _generate_storage_warnings(
        self,
        candidates: List[RankedCandidate],
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

    def _recommend_cli_provider(
        self,
        use_case_config: Dict,
        env: EnvironmentReport,
        hardware: Any,
        user_profile: UserProfile
    ) -> ModuleRecommendation:
        """
        Recommend the best CLI assistant using modern orchestration.
        """
        # 1. Transform EnvironmentReport -> modern HardwareProfile
        from src.services.recommendation.hardware_adapter import HardwareAdapter
        full_hardware = HardwareAdapter.to_profile(env)

        # 2. Execute orchestrator for cli_provider category
        ranked, rejected = self.orchestrator.recommend_models(
            hardware=full_hardware,
            user_profile=user_profile,
            use_case="productivity", # Default CLI use case
            categories=["cli_provider"]
        )

        if not ranked:
            return ModuleRecommendation(
                module_id="cli_provider",
                enabled=False,
                display_name="AI Assistant CLI",
                description="No compatible CLI providers found.",
                config={},
                reasoning=["Hardware or preference mismatch for CLI."],
                warnings=[],
                components=[],
                estimated_size_gb=0,
                estimated_time_minutes=0
            )

        best = ranked[0]
        model = best.scored_candidate.passing_candidate.model
        variant = best.scored_candidate.passing_candidate.variant
        
        # Get provider ID from family (e.g. 'gemini')
        provider_id = model.family
        
        return ModuleRecommendation(
            module_id="cli_provider",
            enabled=True,
            display_name=f"{model.name} (CLI)",
            description=model.description or "AI assistant CLI.",
            config={"provider": provider_id},
            reasoning=[best.explanation],
            warnings=[],
            components=[model.dependencies.package or "@google/gemini-cli"],
            estimated_size_gb=variant.download_size_gb,
            estimated_time_minutes=1
        )
            